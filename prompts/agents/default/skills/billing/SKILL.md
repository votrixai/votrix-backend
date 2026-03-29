---
name: billing
description: "Check payment status, bindbank cards, and guide merchants through adding or updating their payment methods."
type: skill
audience: admin
---

# billing

## Rules

- Always call `check_status` before reporting payment status — never guess.
- Never expose raw error strings. Say "Something went wrong, please try again."
- Keep responses concise.

## Tools

> All commands below are executed via `votrix_run("command")`.

### Check payment status

```
billing.check_status

-> payment_method:<active|not_set_up>
-> free_minutes_remaining:<n>
-> unbilled_usage_cents:<n>
```

### Generate card setup link

```
billing.setup_card

-> setup_url:<stripe_checkout_url>
```

## Flows

### Check status

1. Call `billing.check_status`
2. **Active** → "Your payment method is active. You have X free minutes remaining and $Y in unbilled usage."
3. **Not set up** → proceed to card setup flow

### Add payment method

1. Call `billing.setup_card`, extract URL
2. Reply:
   > "Click the link below to add your payment method. Come back when you're done!"
   >
   > [Add Payment Method](<url>)

### After merchant confirms completion

1. Call `billing.check_status`
2. **Active** → "Your payment method has been added. You're all set!"
3. **Still not set up** → "Looks like it wasn't completed. Here's a new link:" → repeat card setup flow