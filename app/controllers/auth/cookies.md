| SameSite value  | Secure absent | Secure present | Notes            |
| --------------- | ------------- | -------------- | ---------------- |
| `Strict`        | ✅ Valid       | ✅ Valid        | Best security    |
| `Lax`           | ✅ Valid       | ✅ Valid        | Default behavior |
| `None`          | ❌ Invalid     | ✅ Required     | Must use Secure  |
| *(unspecified)* | ✅ Valid       | ✅ Valid        | Defaults to Lax  |