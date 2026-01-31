# Resend Webhook Integration Spec

This document describes how to implement the Resend webhook endpoint in your Next.js application to receive email delivery events.

## Overview

Resend sends webhook events for email delivery status changes. Your Next.js API route will receive these events and update the notification status in MongoDB.

## Webhook Events

Resend sends the following event types:

| Event | Description | Status to Set |
|-------|-------------|---------------|
| `email.sent` | Email accepted by Resend | `sent` |
| `email.delivered` | Email delivered to recipient's mailbox | `delivered` |
| `email.opened` | Recipient opened the email | `opened` |
| `email.clicked` | Recipient clicked a link | `clicked` |
| `email.bounced` | Email bounced (hard or soft) | `bounced` |
| `email.complained` | Recipient marked as spam | `complained` |

## Payload Format

```typescript
interface ResendWebhookPayload {
  type: string;  // e.g., "email.delivered"
  created_at: string;  // ISO 8601 timestamp
  data: {
    email_id: string;  // The Resend email ID (matches resend_id in MongoDB)
    from: string;
    to: string[];
    subject: string;
    // For bounce events:
    bounce_type?: "hard" | "soft";
  };
}
```

## Next.js API Route Implementation

### 1. Install Dependencies

```bash
npm install svix
```

### 2. Environment Variables

Add to your `.env.local`:

```bash
RESEND_SIGNING_SECRET=whsec_xxxxx  # Get from Resend dashboard
MONGODB_URI=mongodb://...
```

### 3. Create the Webhook Route

**File: `app/api/webhooks/resend/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { Webhook } from "svix";
import { MongoClient, ObjectId } from "mongodb";

// Resend webhook payload types
interface ResendWebhookData {
  email_id: string;
  from: string;
  to: string[];
  subject: string;
  bounce_type?: "hard" | "soft";
}

interface ResendWebhookPayload {
  type: string;
  created_at: string;
  data: ResendWebhookData;
}

// Map Resend event types to our notification statuses
const EVENT_TO_STATUS: Record<string, string> = {
  "email.sent": "sent",
  "email.delivered": "delivered",
  "email.opened": "opened",
  "email.clicked": "clicked",
  "email.bounced": "bounced",
  "email.complained": "complained",
};

// Map event types to timestamp fields
const EVENT_TO_TIMESTAMP_FIELD: Record<string, string> = {
  "email.delivered": "delivered_at",
  "email.opened": "opened_at",
  "email.bounced": "bounced_at",
};

export async function POST(request: NextRequest) {
  const SIGNING_SECRET = process.env.RESEND_SIGNING_SECRET;

  if (!SIGNING_SECRET) {
    console.error("Missing RESEND_SIGNING_SECRET");
    return NextResponse.json(
      { error: "Server configuration error" },
      { status: 500 }
    );
  }

  // Get the raw body and headers for signature verification
  const body = await request.text();
  const headers = {
    "svix-id": request.headers.get("svix-id") ?? "",
    "svix-timestamp": request.headers.get("svix-timestamp") ?? "",
    "svix-signature": request.headers.get("svix-signature") ?? "",
  };

  // Verify the webhook signature
  const wh = new Webhook(SIGNING_SECRET);
  let payload: ResendWebhookPayload;

  try {
    payload = wh.verify(body, headers) as ResendWebhookPayload;
  } catch (err) {
    console.error("Webhook signature verification failed:", err);
    return NextResponse.json(
      { error: "Invalid signature" },
      { status: 401 }
    );
  }

  // Extract event data
  const { type: eventType, data, created_at } = payload;
  const { email_id: resendId, bounce_type } = data;

  // Get the new status
  const newStatus = EVENT_TO_STATUS[eventType];
  if (!newStatus) {
    // Unknown event type - acknowledge but don't process
    console.log(`Ignoring unknown event type: ${eventType}`);
    return NextResponse.json({ received: true });
  }

  // Build update document
  const updateFields: Record<string, any> = {
    status: newStatus,
  };

  // Add timestamp field if applicable
  const timestampField = EVENT_TO_TIMESTAMP_FIELD[eventType];
  if (timestampField) {
    updateFields[timestampField] = new Date(created_at);
  }

  // Add bounce type for bounce events
  if (eventType === "email.bounced" && bounce_type) {
    updateFields.bounce_type = bounce_type;
  }

  // Update MongoDB
  const client = new MongoClient(process.env.MONGODB_URI!);

  try {
    await client.connect();
    const db = client.db(process.env.MONGODB_DATABASE || "disaster_response");
    const notifications = db.collection("notifications");

    const result = await notifications.updateOne(
      { resend_id: resendId },
      { $set: updateFields }
    );

    if (result.matchedCount === 0) {
      console.warn(`No notification found for resend_id: ${resendId}`);
    } else {
      console.log(
        `Updated notification ${resendId} to status: ${newStatus}`
      );
    }
  } catch (err) {
    console.error("Database update failed:", err);
    return NextResponse.json(
      { error: "Database error" },
      { status: 500 }
    );
  } finally {
    await client.close();
  }

  return NextResponse.json({ received: true });
}
```

## Setting Up the Webhook in Resend

1. Go to [Resend Dashboard](https://resend.com/webhooks)
2. Click "Add Webhook"
3. Enter your endpoint URL: `https://your-domain.com/api/webhooks/resend`
4. Select the events you want to receive:
   - `email.delivered`
   - `email.opened`
   - `email.bounced`
   - `email.complained`
5. Copy the signing secret and add it to your environment variables

## Testing Webhooks

### Local Development

Use the Resend CLI or a tool like ngrok to test webhooks locally:

```bash
# Install ngrok
npm install -g ngrok

# Start your Next.js dev server
npm run dev

# In another terminal, create a tunnel
ngrok http 3000

# Use the ngrok URL as your webhook endpoint in Resend
```

### Test Email Addresses

Resend provides special email addresses for testing:

| Email | Behavior |
|-------|----------|
| `delivered@resend.dev` | Simulates successful delivery |
| `bounced@resend.dev` | Simulates a bounce |
| `complained@resend.dev` | Simulates a spam complaint |

### Manual Testing

```bash
# Send a test notification to a Resend test address
curl -X POST http://localhost:3000/api/test/send-notification \
  -H "Content-Type: application/json" \
  -d '{"email": "delivered@resend.dev"}'
```

## MongoDB Index Recommendation

For efficient webhook lookups, add an index on the `resend_id` field:

```javascript
db.notifications.createIndex({ "resend_id": 1 });
```

## Error Handling

The webhook endpoint should:

1. **Always return 200** for valid signatures, even if the notification isn't found
2. **Return 401** for invalid signatures
3. **Return 500** for server errors (Resend will retry)

Resend will retry failed webhook deliveries with exponential backoff.

## Security Considerations

1. **Always verify signatures** - Never process webhooks without verifying the svix signature
2. **Use HTTPS** - Webhook endpoints must use HTTPS in production
3. **Idempotency** - Handle duplicate webhook deliveries gracefully (same event may be sent multiple times)
4. **Rate limiting** - Consider adding rate limiting to the webhook endpoint
