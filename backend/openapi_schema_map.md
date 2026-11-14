# Pilot for Trades — OpenAPI Schema Map

**Generated**: 2026-09-06T19:47:03Z  
**Source**: openapi.json  
**Purpose**: Human/agent-readable endpoint summary. Check this before writing any frontend hook or backend route.

---

## Endpoints by Tag

### account-security

#### `GET /api/v1/users/me/data-exports`
**Summary**: List Data Exports  
**Auth**: Required  

**Response 200**: `Response List Data Exports Api V1 Users Me Data Exports Get`
```json
[
  {
    "export_id": "string",
    "status": "string",
    "requested_at": "string",
    "expires_at": "Expires At",
    "signed_url": "Signed Url",
    "data_scope": "string",
    "failure_reason": "Failure Reason"
  }
]
```

---

#### `POST /api/v1/users/me/data-exports`
**Summary**: Create Data Export  
**Auth**: Required  

**Response 201**: `DataExportCreateResponse`
```json
{
  "export_id": "string",
  "status": "string",
  "requested_at": "string"
}
```

---

#### `GET /api/v1/users/me/data-exports/test`
**Summary**: List Data Exports Test  

**Response 200**: `Response List Data Exports Test Api V1 Users Me Data Exports Test Get`
```json
[
  {
    "export_id": "string",
    "status": "string",
    "requested_at": "string",
    "expires_at": "Expires At",
    "signed_url": "Signed Url",
    "data_scope": "string",
    "failure_reason": "Failure Reason"
  }
]
```

---

#### `POST /api/v1/users/me/data-exports/test`
**Summary**: Create Data Export Test  

**Response 201**: `DataExportCreateResponse`
```json
{
  "export_id": "string",
  "status": "string",
  "requested_at": "string"
}
```

---

#### `GET /api/v1/users/me/data-exports/{export_id}`
**Summary**: Get Data Export  
**Auth**: Required  

**Parameters**:
- `export_id` (path, string, required)

**Response 200**: `DataExportStatusResponse`
```json
{
  "export_id": "string",
  "status": "string",
  "requested_at": "string",
  "expires_at": "Expires At",
  "signed_url": "Signed Url",
  "data_scope": "string",
  "failure_reason": "Failure Reason"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/me/data-exports/{export_id}/test`
**Summary**: Get Data Export Test  

**Parameters**:
- `export_id` (path, string, required)

**Response 200**: `DataExportStatusResponse`
```json
{
  "export_id": "string",
  "status": "string",
  "requested_at": "string",
  "expires_at": "Expires At",
  "signed_url": "Signed Url",
  "data_scope": "string",
  "failure_reason": "Failure Reason"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/me/mfa-status`
**Summary**: Get Mfa Status  
**Auth**: Required  

**Response 200**: `MfaStatusResponse`
```json
{
  "enrolled_methods": [
    "string"
  ],
  "methods": [
    {
      "method_id": "...",
      "method_type": "...",
      "enrolled_at": "...",
      "last_used_at": "...",
      "destination_masked": "..."
    }
  ],
  "tenant_policy_required": false,
  "grace_period_active": false,
  "grace_ends_at": "Grace Ends At",
  "enforcement_activated": false
}
```

---

#### `GET /api/v1/users/me/mfa-status/test`
**Summary**: Get Mfa Status Test  

**Response 200**: `MfaStatusResponse`
```json
{
  "enrolled_methods": [
    "string"
  ],
  "methods": [
    {
      "method_id": "...",
      "method_type": "...",
      "enrolled_at": "...",
      "last_used_at": "...",
      "destination_masked": "..."
    }
  ],
  "tenant_policy_required": false,
  "grace_period_active": false,
  "grace_ends_at": "Grace Ends At",
  "enforcement_activated": false
}
```

---

#### `DELETE /api/v1/users/me/mfa/methods/{method_id}`
**Summary**: Delete Mfa Method  
**Auth**: Required  

**Parameters**:
- `method_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/users/me/mfa/methods/{method_id}/test`
**Summary**: Delete Mfa Method Test  

**Parameters**:
- `method_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm`
**Summary**: Enroll Confirm  
**Auth**: Required  

**Parameters**:
- `method_type` (path, string, required)

**Request body**: `MfaEnrollConfirmRequest`
```json
{
  "code": "string"
}
```

**Response 200**: `MfaEnrollConfirmResponse`
```json
{
  "method_id": "string",
  "enrolled_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm/test`
**Summary**: Enroll Confirm Test  

**Parameters**:
- `method_type` (path, string, required)

**Request body**: `MfaEnrollConfirmRequest`
```json
{
  "code": "string"
}
```

**Response 200**: `MfaEnrollConfirmResponse`
```json
{
  "method_id": "string",
  "enrolled_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start`
**Summary**: Enroll Start  
**Auth**: Required  

**Parameters**:
- `method_type` (path, string, required)

**Response 200**: `MfaEnrollStartResponse`
```json
{
  "method_type": "string",
  "qr_code_uri": "Qr Code Uri",
  "secret": "Secret",
  "destination_masked": "Destination Masked"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start/test`
**Summary**: Enroll Start Test  

**Parameters**:
- `method_type` (path, string, required)

**Response 200**: `MfaEnrollStartResponse`
```json
{
  "method_type": "string",
  "qr_code_uri": "Qr Code Uri",
  "secret": "Secret",
  "destination_masked": "Destination Masked"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/me/mfa/recovery-codes/generate`
**Summary**: Generate Recovery Codes  
**Auth**: Required  

**Response 201**: `MfaRecoveryCodesGenerateResponse`
```json
{
  "codes": [
    "string"
  ],
  "set_id": "string"
}
```

---

#### `POST /api/v1/users/me/mfa/recovery-codes/generate/test`
**Summary**: Generate Recovery Codes Test  

**Response 201**: `MfaRecoveryCodesGenerateResponse`
```json
{
  "codes": [
    "string"
  ],
  "set_id": "string"
}
```

---

#### `GET /api/v1/users/me/mfa/recovery-codes/status`
**Summary**: Recovery Codes Status  
**Auth**: Required  

**Response 200**: `MfaRecoveryCodesStatusResponse`
```json
{
  "unused_code_count": 0,
  "last_generated_at": "Last Generated At"
}
```

---

#### `GET /api/v1/users/me/mfa/recovery-codes/status/test`
**Summary**: Recovery Codes Status Test  

**Response 200**: `MfaRecoveryCodesStatusResponse`
```json
{
  "unused_code_count": 0,
  "last_generated_at": "Last Generated At"
}
```

---

#### `GET /api/v1/users/me/session-history`
**Summary**: Get Session History  
**Auth**: Required  

**Response 200**: `SessionHistoryResponse`
```json
{
  "first_login_at": "string",
  "total_session_count": 0,
  "last_login_at": "string"
}
```

---

#### `GET /api/v1/users/me/session-history/test`
**Summary**: Get Session History Test  

**Response 200**: `SessionHistoryResponse`
```json
{
  "first_login_at": "string",
  "total_session_count": 0,
  "last_login_at": "string"
}
```

---

#### `GET /api/v1/users/me/sessions`
**Summary**: Get Sessions  
**Auth**: Required  

**Response 200**: `Response Get Sessions Api V1 Users Me Sessions Get`
```json
[
  {
    "session_id": "string",
    "display_label": "string",
    "ip_address": "string",
    "geolocation": "Geolocation",
    "created_at": "string",
    "last_active_at": "string",
    "is_current": false,
    "revoked_at": "Revoked At"
  }
]
```

---

#### `POST /api/v1/users/me/sessions/revoke-others`
**Summary**: Revoke Others Route  
**Auth**: Required  

**Response 200**: `RevokeOthersResponse`
```json
{
  "revoked_count": 0
}
```

---

#### `POST /api/v1/users/me/sessions/revoke-others/test`
**Summary**: Revoke Others Test  

**Response 200**: `RevokeOthersResponse`
```json
{
  "revoked_count": 0
}
```

---

#### `GET /api/v1/users/me/sessions/test`
**Summary**: Get Sessions Test  

**Response 200**: `Response Get Sessions Test Api V1 Users Me Sessions Test Get`
```json
[
  {
    "session_id": "string",
    "display_label": "string",
    "ip_address": "string",
    "geolocation": "Geolocation",
    "created_at": "string",
    "last_active_at": "string",
    "is_current": false,
    "revoked_at": "Revoked At"
  }
]
```

---

#### `DELETE /api/v1/users/me/sessions/{session_id}`
**Summary**: Revoke Session Route  
**Auth**: Required  

**Parameters**:
- `session_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/users/me/sessions/{session_id}/test`
**Summary**: Revoke Session Test  

**Parameters**:
- `session_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### addresses

#### `GET /api/v1/addresses/`
**Summary**: List Addresses  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Addresses Api V1 Addresses  Get`
```json
[
  {
    "id": "string",
    "line1": "Line1",
    "line2": "Line2",
    "line3": "Line3",
    "city": "City",
    "state": "State",
    "postal_code": "Postal Code",
    "country": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/addresses/`
**Summary**: Create Address  
**Auth**: Required  

**Request body**: `AddressCreate`
```json
{
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string",
  "latitude": "Latitude"
}
```

**Response 201**: `AddressResponse`
```json
{
  "id": "string",
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/addresses/by-entity/{entity_type}/{entity_id}`
**Summary**: Get Addresses By Entity  
**Auth**: Required  

**Parameters**:
- `entity_type` (path, string, required)
- `entity_id` (path, string, required)

**Response 200**: `Response Get Addresses By Entity Api V1 Addresses By Entity  Entity Type   Entity Id  Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/addresses/by-entity/{entity_type}/{entity_id}/test`
**Summary**: Get Addresses By Entity Test  

**Parameters**:
- `entity_type` (path, string, required)
- `entity_id` (path, string, required)

**Response 200**: `Response Get Addresses By Entity Test Api V1 Addresses By Entity  Entity Type   Entity Id  Test Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/addresses/test`
**Summary**: List Addresses Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Addresses Test Api V1 Addresses Test Get`
```json
[
  {
    "id": "string",
    "line1": "Line1",
    "line2": "Line2",
    "line3": "Line3",
    "city": "City",
    "state": "State",
    "postal_code": "Postal Code",
    "country": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/addresses/test`
**Summary**: Create Address Test  

**Request body**: `AddressCreate`
```json
{
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string",
  "latitude": "Latitude"
}
```

**Response 201**: `AddressResponse`
```json
{
  "id": "string",
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/addresses/{address_id}`
**Summary**: Get Address  
**Auth**: Required  

**Parameters**:
- `address_id` (path, string, required)

**Response 200**: `AddressResponse`
```json
{
  "id": "string",
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/addresses/{address_id}`
**Summary**: Update Address  
**Auth**: Required  

**Parameters**:
- `address_id` (path, string, required)

**Request body**: `AddressUpdate`
```json
{
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "Country",
  "latitude": "Latitude"
}
```

**Response 200**: `AddressResponse`
```json
{
  "id": "string",
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/addresses/{address_id}`
**Summary**: Delete Address  
**Auth**: Required  

**Parameters**:
- `address_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/addresses/{address_id}/link-to-entity`
**Summary**: Link Address To Entity  
**Auth**: Required  

**Parameters**:
- `address_id` (path, string, required)

**Request body**: `EntityAddressLink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string",
  "address_type_code": "string",
  "is_primary": false
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/addresses/{address_id}/link-to-entity/test`
**Summary**: Link Address To Entity Test  

**Parameters**:
- `address_id` (path, string, required)

**Request body**: `EntityAddressLink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string",
  "address_type_code": "string",
  "is_primary": false
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/addresses/{address_id}/test`
**Summary**: Get Address Test  

**Parameters**:
- `address_id` (path, string, required)

**Response 200**: `AddressResponse`
```json
{
  "id": "string",
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/addresses/{address_id}/test`
**Summary**: Update Address Test  

**Parameters**:
- `address_id` (path, string, required)

**Request body**: `AddressUpdate`
```json
{
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "Country",
  "latitude": "Latitude"
}
```

**Response 200**: `AddressResponse`
```json
{
  "id": "string",
  "line1": "Line1",
  "line2": "Line2",
  "line3": "Line3",
  "city": "City",
  "state": "State",
  "postal_code": "Postal Code",
  "country": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/addresses/{address_id}/test`
**Summary**: Delete Address Test  

**Parameters**:
- `address_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/addresses/{address_id}/unlink-from-entity`
**Summary**: Unlink Address From Entity  
**Auth**: Required  

**Parameters**:
- `address_id` (path, string, required)

**Request body**: `EntityAddressUnlink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string"
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/addresses/{address_id}/unlink-from-entity/test`
**Summary**: Unlink Address From Entity Test  

**Parameters**:
- `address_id` (path, string, required)

**Request body**: `EntityAddressUnlink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string"
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### admin

#### `POST /api/v1/admin/help/articles/{article_id}/reprocess`
**Summary**: Admin Reprocess Article  
**Auth**: Required  

**Parameters**:
- `article_id` (path, string, required)

**Response 200**: `AdminReprocessResponse`
```json
{
  "status": "string",
  "article_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### admin-tenants

#### `GET /api/v1/admin/tenants/{tenant_id}/overrides`
**Summary**: List tenant feature overrides  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `Response Get Overrides Api V1 Admin Tenants  Tenant Id  Overrides Get`
```json
[
  {
    "product_feature_code": "string",
    "limit_quantity": "Limit Quantity",
    "included_quantity": "Included Quantity",
    "overage_price_cents": "Overage Price Cents",
    "overage_cap_per_period": "Overage Cap Per Period",
    "alert_threshold_pct": "Alert Threshold Pct",
    "enabled": false,
    "tenant_id": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/admin/tenants/{tenant_id}/overrides`
**Summary**: Create or update a tenant feature override  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `TenantOverrideCreate`
```json
{
  "product_feature_code": "string",
  "limit_quantity": "Limit Quantity",
  "included_quantity": "Included Quantity",
  "overage_price_cents": "Overage Price Cents",
  "overage_cap_per_period": "Overage Cap Per Period",
  "alert_threshold_pct": "Alert Threshold Pct",
  "enabled": false
}
```

**Response 201**: `TenantOverrideResponse`
```json
{
  "product_feature_code": "string",
  "limit_quantity": "Limit Quantity",
  "included_quantity": "Included Quantity",
  "overage_price_cents": "Overage Price Cents",
  "overage_cap_per_period": "Overage Cap Per Period",
  "alert_threshold_pct": "Alert Threshold Pct",
  "enabled": false,
  "tenant_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/admin/tenants/{tenant_id}/overrides/test`
**Summary**: [TEST] List tenant feature overrides (no auth)  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `Response Get Overrides Test Api V1 Admin Tenants  Tenant Id  Overrides Test Get`
```json
[
  {
    "product_feature_code": "string",
    "limit_quantity": "Limit Quantity",
    "included_quantity": "Included Quantity",
    "overage_price_cents": "Overage Price Cents",
    "overage_cap_per_period": "Overage Cap Per Period",
    "alert_threshold_pct": "Alert Threshold Pct",
    "enabled": false,
    "tenant_id": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/admin/tenants/{tenant_id}/overrides/test`
**Summary**: [TEST] Create/update tenant feature override (no auth)  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `TenantOverrideCreate`
```json
{
  "product_feature_code": "string",
  "limit_quantity": "Limit Quantity",
  "included_quantity": "Included Quantity",
  "overage_price_cents": "Overage Price Cents",
  "overage_cap_per_period": "Overage Cap Per Period",
  "alert_threshold_pct": "Alert Threshold Pct",
  "enabled": false
}
```

**Response 201**: `TenantOverrideResponse`
```json
{
  "product_feature_code": "string",
  "limit_quantity": "Limit Quantity",
  "included_quantity": "Included Quantity",
  "overage_price_cents": "Overage Price Cents",
  "overage_cap_per_period": "Overage Cap Per Period",
  "alert_threshold_pct": "Alert Threshold Pct",
  "enabled": false,
  "tenant_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### audit

#### `GET /api/v1/audit/diff/{entity_type}/{entity_id}`
**Summary**: Get Field Level Diff  
**Auth**: Required  

**Parameters**:
- `entity_type` (path, string, required)
- `entity_id` (path, string, required)

**Response 200**: `AuditDiffResponse`
```json
{
  "entity_type": "string",
  "entity_id": "string",
  "changes": [
    {
      "field_name": "...",
      "old_value": "...",
      "new_value": "...",
      "changed_at": "...",
      "changed_by": "...",
      "action": "..."
    }
  ],
  "total_changes": 0,
  "first_seen": "First Seen",
  "last_modified": "Last Modified"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/audit/events`
**Summary**: Query Audit Events  
**Auth**: Required  

**Parameters**:
- `entity_type` (query, , optional) — Filter by table name (e.g., 'customer')
- `entity_id` (query, , optional) — Filter by specific entity UUID
- `user_id` (query, , optional) — Filter by user who made the change
- `action` (query, , optional) — Filter by operation: INSERT, UPDATE, DELETE
- `start_date` (query, , optional) — Filter by occurred_at >= start_date
- `end_date` (query, , optional) — Filter by occurred_at <= end_date
- `limit` (query, integer, optional, default: 50) — Max records to return (1-500)
- `offset` (query, integer, optional, default: 0) — Number of records to skip for pagination

**Response 200**: `AuditEventsListResponse`
```json
{
  "events": [
    {
      "id": "...",
      "occurred_at": "...",
      "tenant_id": "...",
      "user_id": "...",
      "entity_name": "...",
      "entity_id": "...",
      "action": "...",
      "old_values": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0,
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/audit/summary`
**Summary**: Get Audit Summary  
**Auth**: Required  

**Parameters**:
- `days` (query, integer, optional, default: 30) — Number of days to analyze

**Response 200**: `Response Get Audit Summary Api V1 Audit Summary Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### auth

#### `POST /api/v1/auth/signup`
**Summary**: Signup  
**Auth**: Required  

**Request body**: `SignupRequest`
```json
{
  "tenant_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name"
}
```

**Response 201**: `SignupResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/auth/signup/test`
**Summary**: Signup Test  

**Parameters**:
- `email` (query, string, required)

**Request body**: `SignupRequest`
```json
{
  "tenant_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name"
}
```

**Response 201**: `SignupResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### catalog

#### `GET /api/v1/catalog/pricebook`
**Summary**: List pricebook items  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `is_active` (query, boolean, optional, default: True)
- `search` (query, , optional)

**Response 200**: `PaginatedCatalogResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "sku": "...",
      "name": "...",
      "description": "...",
      "uom_id": "...",
      "taxability_code": "...",
      "is_active": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/catalog/pricebook`
**Summary**: Create a pricebook item with initial price  
**Auth**: Required  

**Request body**: `PricebookItemCreate`
```json
{
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "initial_price_cents": 0,
  "effective_from": "Effective From"
}
```

**Response 201**: `PricebookItemResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricebook/test`
**Summary**: List pricebook items (TEST — no auth)  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `is_active` (query, boolean, optional, default: True)
- `search` (query, , optional)

**Response 200**: `PaginatedCatalogResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "sku": "...",
      "name": "...",
      "description": "...",
      "uom_id": "...",
      "taxability_code": "...",
      "is_active": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/catalog/pricebook/test`
**Summary**: Create a pricebook item (TEST — no auth)  

**Request body**: `PricebookItemCreate`
```json
{
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "initial_price_cents": 0,
  "effective_from": "Effective From"
}
```

**Response 201**: `PricebookItemResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricebook/{item_id}`
**Summary**: Get a single pricebook item  
**Auth**: Required  

**Parameters**:
- `item_id` (path, string, required)

**Response 200**: `PricebookItemResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/catalog/pricebook/{item_id}`
**Summary**: Update pricebook item metadata  
**Auth**: Required  

**Parameters**:
- `item_id` (path, string, required)

**Request body**: `PricebookItemPatch`
```json
{
  "name": "Name",
  "description": "Description",
  "taxability_code": "Taxability Code",
  "is_active": "Is Active"
}
```

**Response 200**: `PricebookItemResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/catalog/pricebook/{item_id}/price`
**Summary**: Set a new price via temporal supersession  
**Auth**: Required  

**Parameters**:
- `item_id` (path, string, required)

**Request body**: `PricebookItemPriceCreate`
```json
{
  "unit_price_cents": 0,
  "effective_from": "string"
}
```

**Response 201**: `PricebookItemCurrentPriceResponse`
```json
{
  "id": 0,
  "default_unit_price_cents": 0,
  "valid_period_lower": "Valid Period Lower",
  "valid_period_upper": "Valid Period Upper",
  "recorded_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricebook/{item_id}/price-history`
**Summary**: Get price history for a pricebook item  
**Auth**: Required  

**Parameters**:
- `item_id` (path, string, required)

**Response 200**: `Response Get Pricebook Item Price History Api V1 Catalog Pricebook  Item Id  Price History Get`
```json
[
  {
    "id": 0,
    "default_unit_price_cents": 0,
    "valid_period_lower": "Valid Period Lower",
    "valid_period_upper": "Valid Period Upper",
    "recorded_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricebook/{item_id}/price-history/test`
**Summary**: Get price history for a pricebook item (TEST — no auth)  

**Parameters**:
- `item_id` (path, string, required)

**Response 200**: `Response Get Pricebook Item Price History Test Api V1 Catalog Pricebook  Item Id  Price History Test Get`
```json
[
  {
    "id": 0,
    "default_unit_price_cents": 0,
    "valid_period_lower": "Valid Period Lower",
    "valid_period_upper": "Valid Period Upper",
    "recorded_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/catalog/pricebook/{item_id}/price/test`
**Summary**: Set a new price via temporal supersession (TEST — no auth)  

**Parameters**:
- `item_id` (path, string, required)

**Request body**: `PricebookItemPriceCreate`
```json
{
  "unit_price_cents": 0,
  "effective_from": "string"
}
```

**Response 201**: `PricebookItemCurrentPriceResponse`
```json
{
  "id": 0,
  "default_unit_price_cents": 0,
  "valid_period_lower": "Valid Period Lower",
  "valid_period_upper": "Valid Period Upper",
  "recorded_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricebook/{item_id}/test`
**Summary**: Get a single pricebook item (TEST — no auth)  

**Parameters**:
- `item_id` (path, string, required)

**Response 200**: `PricebookItemResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/catalog/pricebook/{item_id}/test`
**Summary**: Update pricebook item metadata (TEST — no auth)  

**Parameters**:
- `item_id` (path, string, required)

**Request body**: `PricebookItemPatch`
```json
{
  "name": "Name",
  "description": "Description",
  "taxability_code": "Taxability Code",
  "is_active": "Is Active"
}
```

**Response 200**: `PricebookItemResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "Uom Id",
  "taxability_code": "Taxability Code",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricing-cache`
**Summary**: Get Pricing Cache  
**Auth**: Required  

**Parameters**:
- `sku` (query, , optional)

**Response 200**: `Response Get Pricing Cache Api V1 Catalog Pricing Cache Get`
```json
[
  {
    "supplier_id": "string",
    "sku": "string",
    "price_cents": 0,
    "currency": "string",
    "expires_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/pricing-cache/test`
**Summary**: Get Pricing Cache Test  

**Parameters**:
- `sku` (query, , optional)

**Response 200**: `Response Get Pricing Cache Test Api V1 Catalog Pricing Cache Test Get`
```json
[
  {
    "supplier_id": "string",
    "sku": "string",
    "price_cents": 0,
    "currency": "string",
    "expires_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/supplier-items`
**Summary**: List Supplier Items  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Supplier Items Api V1 Catalog Supplier Items Get`
```json
[
  {
    "id": "string",
    "tenant_id": "Tenant Id",
    "supplier_id": "string",
    "sku": "string",
    "name": "string",
    "description": "Description",
    "uom_id": "string",
    "is_active": false
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/catalog/supplier-items`
**Summary**: Create Supplier Item  
**Auth**: Required  

**Request body**: `SupplierItemCreate`
```json
{
  "supplier_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "string",
  "category_id": "Category Id",
  "taxability_code": "Taxability Code"
}
```

**Response 201**: `SupplierItemResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "supplier_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "string",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/catalog/supplier-items/test`
**Summary**: List Supplier Items Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Supplier Items Test Api V1 Catalog Supplier Items Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "Tenant Id",
    "supplier_id": "string",
    "sku": "string",
    "name": "string",
    "description": "Description",
    "uom_id": "string",
    "is_active": false
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/catalog/supplier-items/test`
**Summary**: Create Supplier Item Test  

**Request body**: `SupplierItemCreate`
```json
{
  "supplier_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "string",
  "category_id": "Category Id",
  "taxability_code": "Taxability Code"
}
```

**Response 201**: `SupplierItemResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "supplier_id": "string",
  "sku": "string",
  "name": "string",
  "description": "Description",
  "uom_id": "string",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### communications

#### `GET /api/v1/communications/comm-template-types`
**Summary**: List Comm Template Types  
**Auth**: Required  

**Parameters**:
- `category` (query, , optional) — Filter by lifecycle category
- `initiator` (query, , optional) — Filter by initiator: tech, owner, system

**Response 200**: `CommTemplateTypeListResponse`
```json
{
  "total": 0,
  "items": [
    {
      "code": "...",
      "slug": "...",
      "name": "...",
      "description": "...",
      "category": "...",
      "preferred_channel": "...",
      "initiator": "...",
      "requires_approval": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/comm-template-types/test`
**Summary**: List Comm Template Types Test  

**Parameters**:
- `category` (query, , optional)
- `initiator` (query, , optional)

**Response 200**: `CommTemplateTypeListResponse`
```json
{
  "total": 0,
  "items": [
    {
      "code": "...",
      "slug": "...",
      "name": "...",
      "description": "...",
      "category": "...",
      "preferred_channel": "...",
      "initiator": "...",
      "requires_approval": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/preview`
**Summary**: Preview Communication  
**Auth**: Required  

**Request body**: `CommunicationPreviewRequest`
```json
{
  "customer_id": "string",
  "template_code": "string",
  "variables": {},
  "channel_override": "Channel Override"
}
```

**Response 200**: `CommunicationPreviewResponse`
```json
{
  "rendered_subject": "Rendered Subject",
  "rendered_body": "string",
  "recipient_name": "string",
  "recipient_address": "string",
  "actual_channel": "string",
  "editable_variables": [
    {
      "name": "...",
      "current_value": "...",
      "description": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/preview/test`
**Summary**: Preview Communication Test  

**Request body**: `CommunicationPreviewRequest`
```json
{
  "customer_id": "string",
  "template_code": "string",
  "variables": {},
  "channel_override": "Channel Override"
}
```

**Response 200**: `CommunicationPreviewResponse`
```json
{
  "rendered_subject": "Rendered Subject",
  "rendered_body": "string",
  "recipient_name": "string",
  "recipient_address": "string",
  "actual_channel": "string",
  "editable_variables": [
    {
      "name": "...",
      "current_value": "...",
      "description": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/recent`
**Summary**: Cross-customer recent communications aggregate (COMMS-UI-B1)  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)
- `customer_search` (query, , optional)
- `channel` (query, , optional) — sms | email (email has no data today)
- `sent_from` (query, , optional)
- `sent_to` (query, , optional)

**Response 200**: `RecentCommunicationsResponse`
```json
{
  "items": [
    {
      "id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "channel": "...",
      "direction": "...",
      "body": "...",
      "created_at": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/recent/test`
**Summary**: [TEST] Cross-customer recent communications aggregate (no JWT)  

**Parameters**:
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)
- `customer_search` (query, , optional)
- `channel` (query, , optional) — sms | email (email has no data today)
- `sent_from` (query, , optional)
- `sent_to` (query, , optional)

**Response 200**: `RecentCommunicationsResponse`
```json
{
  "items": [
    {
      "id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "channel": "...",
      "direction": "...",
      "body": "...",
      "created_at": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/send`
**Summary**: Send Communication  
**Auth**: Required  

**Request body**: `CommunicationSendRequest`
```json
{
  "customer_id": "string",
  "template_code": "string",
  "job_id": "Job Id",
  "variables": {},
  "channel_override": "Channel Override"
}
```

**Response 201**: `CommunicationSendResponse`
```json
{
  "communication_id": "string",
  "template_code": "string",
  "actual_channel": "string",
  "channel_override_flag": false,
  "status": "string",
  "rendered_message": "string",
  "rendered_subject": "Rendered Subject",
  "recipient_address": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/send/test`
**Summary**: Send Communication Test  

**Request body**: `CommunicationSendRequest`
```json
{
  "customer_id": "string",
  "template_code": "string",
  "job_id": "Job Id",
  "variables": {},
  "channel_override": "Channel Override"
}
```

**Response 201**: `CommunicationSendResponse`
```json
{
  "communication_id": "string",
  "template_code": "string",
  "actual_channel": "string",
  "channel_override_flag": false,
  "status": "string",
  "rendered_message": "string",
  "rendered_subject": "Rendered Subject",
  "recipient_address": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/test/threads/{thread_id}/messages`
**Summary**: [TEST] Get thread messages — no auth  

**Parameters**:
- `thread_id` (path, string, required)
- `limit` (query, integer, optional, default: 20)
- `before` (query, , optional)

**Response 200**: `MessageListResponse`
```json
{
  "messages": [
    {
      "message_id": "...",
      "direction": "...",
      "body": "...",
      "status": "...",
      "segment_count": "...",
      "sent_at": "...",
      "received_at": "...",
      "delivered_at": "..."
    }
  ],
  "next_cursor": "Next Cursor"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/threads/test/{thread_id}/reply`
**Summary**: [TEST] Send reply — no auth  

**Parameters**:
- `thread_id` (path, string, required)

**Request body**: `ReplyRequest`
```json
{
  "body": "string",
  "composition_method": "string",
  "voice_audio_id": "Voice Audio Id",
  "expected_updated_at": "Expected Updated At"
}
```

**Response 201**: `ReplyResponse`
```json
{
  "message_id": "string",
  "thread_id": "string",
  "direction": "string",
  "body": "string",
  "segment_count": 0,
  "status": "string",
  "carrier_message_id": "Carrier Message Id",
  "sent_at": "Sent At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/threads/{thread_id}/mark-read`
**Summary**: Mark all unread messages in a thread as read for the requesting user  
**Auth**: Required  

**Parameters**:
- `thread_id` (path, string, required)

**Response 200**: `MarkReadResponse`
```json
{
  "marked_read_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/threads/{thread_id}/mark-read/test`
**Summary**: Mark all unread messages in a thread as read (TEST — no auth)  

**Parameters**:
- `thread_id` (path, string, required)

**Response 200**: `MarkReadResponse`
```json
{
  "marked_read_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/threads/{thread_id}/messages`
**Summary**: Get paginated messages for a thread  
**Auth**: Required  

**Parameters**:
- `thread_id` (path, string, required)
- `limit` (query, integer, optional, default: 20)
- `before` (query, , optional)

**Response 200**: `MessageListResponse`
```json
{
  "messages": [
    {
      "message_id": "...",
      "direction": "...",
      "body": "...",
      "status": "...",
      "segment_count": "...",
      "sent_at": "...",
      "received_at": "...",
      "delivered_at": "..."
    }
  ],
  "next_cursor": "Next Cursor"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/threads/{thread_id}/reply`
**Summary**: Send a free-form SMS reply on a thread  
**Auth**: Required  

**Parameters**:
- `thread_id` (path, string, required)

**Request body**: `ReplyRequest`
```json
{
  "body": "string",
  "composition_method": "string",
  "voice_audio_id": "Voice Audio Id",
  "expected_updated_at": "Expected Updated At"
}
```

**Response 201**: `ReplyResponse`
```json
{
  "message_id": "string",
  "thread_id": "string",
  "direction": "string",
  "body": "string",
  "segment_count": 0,
  "status": "string",
  "carrier_message_id": "Carrier Message Id",
  "sent_at": "Sent At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/unrouted`
**Summary**: List unrouted inbound messages  
**Auth**: Required  

**Parameters**:
- `status` (query, string, optional, default: parked)
- `limit` (query, integer, optional, default: 20)
- `before` (query, , optional)

**Response 200**: `UnroutedListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "from_number": "...",
      "body": "...",
      "received_at": "...",
      "status": "..."
    }
  ],
  "next_cursor": "Next Cursor"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/communications/unrouted/test`
**Summary**: List unrouted inbound messages (TEST — no auth)  

**Parameters**:
- `status` (query, string, optional, default: parked)
- `limit` (query, integer, optional, default: 20)
- `before` (query, , optional)

**Response 200**: `UnroutedListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "from_number": "...",
      "body": "...",
      "received_at": "...",
      "status": "..."
    }
  ],
  "next_cursor": "Next Cursor"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/unrouted/{unrouted_id}/assign-to-thread`
**Summary**: Assign an unrouted message to an existing thread  
**Auth**: Required  

**Parameters**:
- `unrouted_id` (path, string, required)

**Request body**: `AssignToThreadRequest`
```json
{
  "thread_id": "string"
}
```

**Response 200**: `AssignToThreadResponse`
```json
{
  "id": "string",
  "status": "string",
  "resolved_thread_id": "Resolved Thread Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/communications/unrouted/{unrouted_id}/assign-to-thread/test`
**Summary**: Assign an unrouted message to an existing thread (TEST — no auth)  

**Parameters**:
- `unrouted_id` (path, string, required)

**Request body**: `AssignToThreadRequest`
```json
{
  "thread_id": "string"
}
```

**Response 200**: `AssignToThreadResponse`
```json
{
  "id": "string",
  "status": "string",
  "resolved_thread_id": "Resolved Thread Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/test/{customer_id}/communications`
**Summary**: Get Customer Communications Test  

**Parameters**:
- `customer_id` (path, string, required)
- `page` (query, integer, optional, default: 1)
- `page_size` (query, integer, optional, default: 20)

**Response 200**: `CommunicationHistoryResponse`
```json
{
  "customer_id": "string",
  "total": 0,
  "page": 0,
  "page_size": 0,
  "items": [
    {
      "communication_id": "...",
      "template_code": "...",
      "actual_channel": "...",
      "channel_override_flag": "...",
      "customer_preferred_channel": "...",
      "rendered_message": "...",
      "rendered_subject": "...",
      "status": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/test/{customer_id}/threads`
**Summary**: Get Customer Sms Threads Test  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `CustomerSmsThreadsResponse`
```json
{
  "threads": [
    {
      "thread_id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "customer_phone": "...",
      "customer_sms_opted_out": "...",
      "customer_opted_out_at": "...",
      "tech_id": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/{customer_id}/communications`
**Summary**: Get Customer Communications  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)
- `page` (query, integer, optional, default: 1)
- `page_size` (query, integer, optional, default: 20)

**Response 200**: `CommunicationHistoryResponse`
```json
{
  "customer_id": "string",
  "total": 0,
  "page": 0,
  "page_size": 0,
  "items": [
    {
      "communication_id": "...",
      "template_code": "...",
      "actual_channel": "...",
      "channel_override_flag": "...",
      "customer_preferred_channel": "...",
      "rendered_message": "...",
      "rendered_subject": "...",
      "status": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/{customer_id}/threads`
**Summary**: Get Customer Sms Threads  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `CustomerSmsThreadsResponse`
```json
{
  "threads": [
    {
      "thread_id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "customer_phone": "...",
      "customer_sms_opted_out": "...",
      "customer_opted_out_at": "...",
      "tech_id": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### contacts

#### `GET /api/v1/contacts/`
**Summary**: List Contacts  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Contacts Api V1 Contacts  Get`
```json
[
  {
    "id": "string",
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "Email",
    "mobile_phone": "Mobile Phone",
    "locale": "Locale",
    "timezone": "Timezone",
    "notes": "Notes"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/contacts/`
**Summary**: Create Contact  
**Auth**: Required  

**Request body**: `ContactCreate`
```json
{
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 201**: `ContactResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/contacts/by-entity/{entity_type}/{entity_id}`
**Summary**: Get Contacts By Entity  
**Auth**: Required  

**Parameters**:
- `entity_type` (path, string, required)
- `entity_id` (path, string, required)

**Response 200**: `Response Get Contacts By Entity Api V1 Contacts By Entity  Entity Type   Entity Id  Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/contacts/by-entity/{entity_type}/{entity_id}/test`
**Summary**: Get Contacts By Entity Test  

**Parameters**:
- `entity_type` (path, string, required)
- `entity_id` (path, string, required)

**Response 200**: `Response Get Contacts By Entity Test Api V1 Contacts By Entity  Entity Type   Entity Id  Test Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/contacts/test`
**Summary**: List Contacts Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Contacts Test Api V1 Contacts Test Get`
```json
[
  {
    "id": "string",
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "Email",
    "mobile_phone": "Mobile Phone",
    "locale": "Locale",
    "timezone": "Timezone",
    "notes": "Notes"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/contacts/test`
**Summary**: Create Contact Test  

**Request body**: `ContactCreate`
```json
{
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 201**: `ContactResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/contacts/{contact_id}`
**Summary**: Get Contact  
**Auth**: Required  

**Parameters**:
- `contact_id` (path, string, required)

**Response 200**: `ContactResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/contacts/{contact_id}`
**Summary**: Update Contact  
**Auth**: Required  

**Parameters**:
- `contact_id` (path, string, required)

**Request body**: `ContactUpdate`
```json
{
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes",
  "is_active": "Is Active"
}
```

**Response 200**: `ContactResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/contacts/{contact_id}`
**Summary**: Delete Contact  
**Auth**: Required  

**Parameters**:
- `contact_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/contacts/{contact_id}/link-to-entity`
**Summary**: Link Contact To Entity  
**Auth**: Required  

**Parameters**:
- `contact_id` (path, string, required)

**Request body**: `EntityContactLink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string",
  "contact_type_code": "string",
  "is_primary": false
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/contacts/{contact_id}/link-to-entity/test`
**Summary**: Link Contact To Entity Test  

**Parameters**:
- `contact_id` (path, string, required)

**Request body**: `EntityContactLink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string",
  "contact_type_code": "string",
  "is_primary": false
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/contacts/{contact_id}/test`
**Summary**: Get Contact Test  

**Parameters**:
- `contact_id` (path, string, required)

**Response 200**: `ContactResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/contacts/{contact_id}/test`
**Summary**: Update Contact Test  

**Parameters**:
- `contact_id` (path, string, required)

**Request body**: `ContactUpdate`
```json
{
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes",
  "is_active": "Is Active"
}
```

**Response 200**: `ContactResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "locale": "Locale",
  "timezone": "Timezone",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/contacts/{contact_id}/test`
**Summary**: Delete Contact Test  

**Parameters**:
- `contact_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/contacts/{contact_id}/unlink-from-entity`
**Summary**: Unlink Contact From Entity  
**Auth**: Required  

**Parameters**:
- `contact_id` (path, string, required)

**Request body**: `EntityContactUnlink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string"
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/contacts/{contact_id}/unlink-from-entity/test`
**Summary**: Unlink Contact From Entity Test  

**Parameters**:
- `contact_id` (path, string, required)

**Request body**: `EntityContactUnlink`
```json
{
  "entity_type_code": "string",
  "entity_id": "string"
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### customers

#### `GET /api/v1/customers/`
**Summary**: List Customers  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `search` (query, , optional)
- `status` (query, , optional)

**Response 200**: `PaginatedCustomerResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "type": "...",
      "display_name": "...",
      "first_name": "...",
      "last_name": "...",
      "company_name": "...",
      "email": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/customers/`
**Summary**: Create Customer  
**Auth**: Required  

**Request body**: `CustomerCreate`
```json
{
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "taxability_code": "Taxability Code"
}
```

**Response 201**: `CustomerResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/test`
**Summary**: List Customers Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `search` (query, , optional)
- `status` (query, , optional)

**Response 200**: `PaginatedCustomerResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "type": "...",
      "display_name": "...",
      "first_name": "...",
      "last_name": "...",
      "company_name": "...",
      "email": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/customers/test`
**Summary**: Create Customer Test  

**Request body**: `CustomerCreate`
```json
{
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "taxability_code": "Taxability Code"
}
```

**Response 201**: `CustomerResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/{customer_id}`
**Summary**: Get Customer  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `CustomerResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/customers/{customer_id}`
**Summary**: Update Customer  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)

**Request body**: `CustomerCreate`
```json
{
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "taxability_code": "Taxability Code"
}
```

**Response 200**: `CustomerResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/customers/{customer_id}`
**Summary**: Delete Customer  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/{customer_id}/payment-methods`
**Summary**: List Payment Methods  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `Response List Payment Methods Api V1 Customers  Customer Id  Payment Methods Get`
```json
[
  {
    "id": "string",
    "customer_id": "Customer Id",
    "tenant_id": "string",
    "payment_type_id": "string",
    "brand": "Brand",
    "psp_provider": "string",
    "psp_payment_method_id": "string",
    "exp_month": "Exp Month"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/customers/{customer_id}/payment-methods`
**Summary**: Create Payment Method  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)

**Request body**: `PaymentMethodCreate`
```json
{
  "psp_payment_method_id": "string",
  "payment_type_id": "string"
}
```

**Response 201**: `PaymentMethodResponse`
```json
{
  "id": "string",
  "customer_id": "Customer Id",
  "tenant_id": "string",
  "payment_type_id": "string",
  "brand": "Brand",
  "psp_provider": "string",
  "psp_payment_method_id": "string",
  "exp_month": "Exp Month"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/{customer_id}/payment-methods/test`
**Summary**: List Payment Methods Test  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `Response List Payment Methods Test Api V1 Customers  Customer Id  Payment Methods Test Get`
```json
[
  {
    "id": "string",
    "customer_id": "Customer Id",
    "tenant_id": "string",
    "payment_type_id": "string",
    "brand": "Brand",
    "psp_provider": "string",
    "psp_payment_method_id": "string",
    "exp_month": "Exp Month"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/customers/{customer_id}/payment-methods/test`
**Summary**: Create Payment Method Test  

**Parameters**:
- `customer_id` (path, string, required)

**Request body**: `PaymentMethodCreate`
```json
{
  "psp_payment_method_id": "string",
  "payment_type_id": "string"
}
```

**Response 201**: `PaymentMethodResponse`
```json
{
  "id": "string",
  "customer_id": "Customer Id",
  "tenant_id": "string",
  "payment_type_id": "string",
  "brand": "Brand",
  "psp_provider": "string",
  "psp_payment_method_id": "string",
  "exp_month": "Exp Month"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/customers/{customer_id}/payment-methods/{pm_id}`
**Summary**: Delete Payment Method  
**Auth**: Required  

**Parameters**:
- `customer_id` (path, string, required)
- `pm_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/customers/{customer_id}/payment-methods/{pm_id}/test`
**Summary**: Delete Payment Method Test  

**Parameters**:
- `customer_id` (path, string, required)
- `pm_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/customers/{customer_id}/test`
**Summary**: Get Customer Test  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `CustomerResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/customers/{customer_id}/test`
**Summary**: Update Customer Test  

**Parameters**:
- `customer_id` (path, string, required)

**Request body**: `CustomerCreate`
```json
{
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email",
  "mobile_phone": "Mobile Phone",
  "taxability_code": "Taxability Code"
}
```

**Response 200**: `CustomerResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "type": "string",
  "display_name": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "company_name": "Company Name",
  "email": "Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/customers/{customer_id}/test`
**Summary**: Delete Customer Test  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### dashboard

#### `GET /api/v1/dashboard/at-risk-jobs`
**Summary**: At-Risk Jobs widget — FE-B23/A1  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 10)

**Response 200**: `AtRiskJobsResponse`
```json
{
  "jobs": [
    {
      "job_id": "...",
      "customer_name": "...",
      "site_name": "...",
      "status_code": "...",
      "scheduled_start_at": "...",
      "actual_cost_cents": "...",
      "quoted_budget_cents": "...",
      "projected_margin_pct": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/dashboard/at-risk-jobs/test`
**Summary**: At-Risk Jobs widget (TEST — no auth)  

**Parameters**:
- `limit` (query, integer, optional, default: 10)

**Response 200**: `AtRiskJobsResponse`
```json
{
  "jobs": [
    {
      "job_id": "...",
      "customer_name": "...",
      "site_name": "...",
      "status_code": "...",
      "scheduled_start_at": "...",
      "actual_cost_cents": "...",
      "quoted_budget_cents": "...",
      "projected_margin_pct": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/dashboard/pending-approvals-summary`
**Summary**: Pending Approvals Summary — FE-B23/A2  
**Auth**: Required  

**Response 200**: `PendingApprovalsSummaryResponse`
```json
{
  "pending_quotes": 0,
  "pending_field_issues": 0
}
```

---

#### `GET /api/v1/dashboard/pending-approvals-summary/test`
**Summary**: Pending Approvals Summary (TEST — no auth)  

**Response 200**: `PendingApprovalsSummaryResponse`
```json
{
  "pending_quotes": 0,
  "pending_field_issues": 0
}
```

---

#### `GET /api/v1/dashboard/widgets`
**Summary**: List Dashboard Widgets  
**Auth**: Required  

**Response 200**: `Response List Widgets Api V1 Dashboard Widgets Get`
```json
[
  {
    "id": "string",
    "user_id": "string",
    "tenant_id": "string",
    "widget_type": "string",
    "widget_config_json": {},
    "position_x": 0,
    "position_y": 0,
    "width": 0
  }
]
```

---

#### `POST /api/v1/dashboard/widgets`
**Summary**: Create Dashboard Widget  
**Auth**: Required  

**Request body**: `UserDashboardWidgetCreate`
```json
{
  "widget_type": "string",
  "widget_config_json": {},
  "position_x": 0,
  "position_y": 0,
  "width": 0,
  "height": 0
}
```

**Response 201**: `UserDashboardWidgetResponse`
```json
{
  "id": "string",
  "user_id": "string",
  "tenant_id": "string",
  "widget_type": "string",
  "widget_config_json": {},
  "position_x": 0,
  "position_y": 0,
  "width": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/dashboard/widgets/recent-customer-messages`
**Summary**: Recent inbound customer messages widget — B11/A64  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 10)

**Response 200**: `RecentCustomerMessagesResponse`
```json
{
  "messages": [
    {
      "thread_id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "tech_id": "...",
      "tech_name": "...",
      "direction": "...",
      "body_preview": "...",
      "last_message_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/dashboard/widgets/recent-customer-messages/test`
**Summary**: Recent inbound customer messages widget (TEST — no auth)  

**Parameters**:
- `limit` (query, integer, optional, default: 10)

**Response 200**: `RecentCustomerMessagesResponse`
```json
{
  "messages": [
    {
      "thread_id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "tech_id": "...",
      "tech_name": "...",
      "direction": "...",
      "body_preview": "...",
      "last_message_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/dashboard/widgets/test`
**Summary**: List Dashboard Widgets (TEST — no auth)  

**Response 200**: `Response List Widgets Test Api V1 Dashboard Widgets Test Get`
```json
[
  {
    "id": "string",
    "user_id": "string",
    "tenant_id": "string",
    "widget_type": "string",
    "widget_config_json": {},
    "position_x": 0,
    "position_y": 0,
    "width": 0
  }
]
```

---

#### `POST /api/v1/dashboard/widgets/test`
**Summary**: Create Dashboard Widget (TEST — no auth)  

**Request body**: `UserDashboardWidgetCreate`
```json
{
  "widget_type": "string",
  "widget_config_json": {},
  "position_x": 0,
  "position_y": 0,
  "width": 0,
  "height": 0
}
```

**Response 201**: `UserDashboardWidgetResponse`
```json
{
  "id": "string",
  "user_id": "string",
  "tenant_id": "string",
  "widget_type": "string",
  "widget_config_json": {},
  "position_x": 0,
  "position_y": 0,
  "width": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/dashboard/widgets/{widget_id}`
**Summary**: Update Dashboard Widget  
**Auth**: Required  

**Parameters**:
- `widget_id` (path, string, required)

**Request body**: `UserDashboardWidgetUpdate`
```json
{
  "widget_config_json": "Widget Config Json",
  "position_x": "Position X",
  "position_y": "Position Y",
  "width": "Width",
  "height": "Height"
}
```

**Response 200**: `UserDashboardWidgetResponse`
```json
{
  "id": "string",
  "user_id": "string",
  "tenant_id": "string",
  "widget_type": "string",
  "widget_config_json": {},
  "position_x": 0,
  "position_y": 0,
  "width": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/dashboard/widgets/{widget_id}`
**Summary**: Delete Dashboard Widget  
**Auth**: Required  

**Parameters**:
- `widget_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/dashboard/widgets/{widget_id}/test`
**Summary**: Update Dashboard Widget (TEST — no auth)  

**Parameters**:
- `widget_id` (path, string, required)

**Request body**: `UserDashboardWidgetUpdate`
```json
{
  "widget_config_json": "Widget Config Json",
  "position_x": "Position X",
  "position_y": "Position Y",
  "width": "Width",
  "height": "Height"
}
```

**Response 200**: `UserDashboardWidgetResponse`
```json
{
  "id": "string",
  "user_id": "string",
  "tenant_id": "string",
  "widget_type": "string",
  "widget_config_json": {},
  "position_x": 0,
  "position_y": 0,
  "width": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/dashboard/widgets/{widget_id}/test`
**Summary**: Delete Dashboard Widget (TEST — no auth)  

**Parameters**:
- `widget_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### health

#### `GET /api/v1/health/celery`
**Summary**: Celery Health  

**Response 200**: `CeleryHealthResponse`
```json
{
  "status": "string",
  "workers_active": 0,
  "broker_connected": false,
  "scheduled_tasks": 0,
  "timestamp": "string"
}
```

---

### help

#### `POST /api/v1/feedback/`
**Summary**: Submit Feedback  
**Auth**: Required  

**Request body**: `FeedbackSubmitRequest`
```json
{
  "category": "string",
  "body": "string",
  "from_help_chat_session_id": "From Help Chat Session Id"
}
```

**Response 201**: `FeedbackSubmitResponse`
```json
{
  "submission_id": "string",
  "category": "string",
  "submitted_at": "string",
  "confirmation_message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/feedback/test`
**Summary**: Submit Feedback Test Alt  

**Request body**: `FeedbackSubmitRequest`
```json
{
  "category": "string",
  "body": "string",
  "from_help_chat_session_id": "From Help Chat Session Id"
}
```

**Response 201**: `FeedbackSubmitResponse`
```json
{
  "submission_id": "string",
  "category": "string",
  "submitted_at": "string",
  "confirmation_message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/help/articles/{article_id}`
**Summary**: Get Help Article  
**Auth**: Required  

**Parameters**:
- `article_id` (path, string, required)

**Response 200**: `HelpArticleResponse`
```json
{
  "article_id": "string",
  "title": "string",
  "category": "string",
  "content_markdown": "string",
  "audience": [
    "string"
  ],
  "last_updated": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/chat`
**Summary**: Help Chat  
**Auth**: Required  

**Request body**: `HelpChatRequest`
```json
{
  "session_id": "Session Id",
  "message": "string",
  "context_payload": "object"
}
```

**Response 200**: `HelpChatResponse`
```json
{
  "session_id": "string",
  "message_id": "string",
  "role": "string",
  "content": "string",
  "retrieved_article_ids": [
    "string"
  ],
  "session_title": "Session Title"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/chat/test`
**Summary**: Help Chat Test  

**Request body**: `HelpChatRequest`
```json
{
  "session_id": "Session Id",
  "message": "string",
  "context_payload": "object"
}
```

**Response 200**: `HelpChatResponse`
```json
{
  "session_id": "string",
  "message_id": "string",
  "role": "string",
  "content": "string",
  "retrieved_article_ids": [
    "string"
  ],
  "session_title": "Session Title"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/feedback/test`
**Summary**: Submit Feedback Test  

**Request body**: `FeedbackSubmitRequest`
```json
{
  "category": "string",
  "body": "string",
  "from_help_chat_session_id": "From Help Chat Session Id"
}
```

**Response 201**: `FeedbackSubmitResponse`
```json
{
  "submission_id": "string",
  "category": "string",
  "submitted_at": "string",
  "confirmation_message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/retrieve`
**Summary**: Retrieve Help Chunks  
**Auth**: Required  

**Request body**: `HelpRetrieveRequest`
```json
{
  "query_embedding": [
    0.0
  ],
  "role": "string",
  "category_hint": "Category Hint",
  "k": 0
}
```

**Response 200**: `HelpRetrieveResponse`
```json
{
  "chunks": [
    {
      "chunk_id": "...",
      "article_id": "...",
      "section_title": "...",
      "chunk_text": "...",
      "score": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/help/sessions`
**Summary**: List Help Sessions  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `HelpSessionListResponse`
```json
{
  "sessions": [
    {
      "id": "...",
      "title": "...",
      "outcome": "...",
      "message_count": "...",
      "last_activity_at": "...",
      "started_at": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/sessions/delete-all`
**Summary**: Delete All Help Sessions  
**Auth**: Required  

**Response 501**: Successful Response

---

#### `GET /api/v1/help/sessions/test`
**Summary**: List Sessions Test  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `HelpSessionListResponse`
```json
{
  "sessions": [
    {
      "id": "...",
      "title": "...",
      "outcome": "...",
      "message_count": "...",
      "last_activity_at": "...",
      "started_at": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/help/sessions/{session_id}`
**Summary**: Get Help Session  
**Auth**: Required  

**Parameters**:
- `session_id` (path, string, required)

**Response 200**: `HelpSessionDetailResponse`
```json
{
  "session_id": "string",
  "title": "Title",
  "outcome": "Outcome",
  "messages": [
    {
      "message_id": "...",
      "role": "...",
      "content": "...",
      "created_at": "...",
      "voice_used": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/help/sessions/{session_id}`
**Summary**: Delete Help Session  
**Auth**: Required  

**Parameters**:
- `session_id` (path, string, required)

**Response 200**: `HelpSessionDeleteResponse`
```json
{
  "message": "string",
  "session_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/sessions/{session_id}/feedback`
**Summary**: Submit Session Feedback  
**Auth**: Required  

**Parameters**:
- `session_id` (path, string, required)

**Request body**: `HelpSessionFeedbackRequest`
```json
{
  "signal": "string"
}
```

**Response 200**: `HelpSessionFeedbackResponse`
```json
{
  "session_id": "string",
  "outcome": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/help/sessions/{session_id}/feedback/test`
**Summary**: Submit Session Feedback Test  

**Parameters**:
- `session_id` (path, string, required)

**Request body**: `HelpSessionFeedbackRequest`
```json
{
  "signal": "string"
}
```

**Response 200**: `HelpSessionFeedbackResponse`
```json
{
  "session_id": "string",
  "outcome": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/help/sessions/{session_id}/test`
**Summary**: Get Help Session Test  

**Parameters**:
- `session_id` (path, string, required)

**Response 200**: `HelpSessionDetailResponse`
```json
{
  "session_id": "string",
  "title": "Title",
  "outcome": "Outcome",
  "messages": [
    {
      "message_id": "...",
      "role": "...",
      "content": "...",
      "created_at": "...",
      "voice_used": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/help/sessions/{session_id}/test`
**Summary**: Delete Help Session Test  

**Parameters**:
- `session_id` (path, string, required)

**Response 200**: `HelpSessionDeleteResponse`
```json
{
  "message": "string",
  "session_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### integrations

#### `GET /api/v1/integrations/calendar/auth`
**Summary**: Initiate Calendar Oauth  
**Auth**: Required  

**Response 200**: Successful Response

---

#### `GET /api/v1/integrations/calendar/auth/test`
**Summary**: Initiate Calendar Oauth Test  

**Response 200**: Successful Response

---

#### `GET /api/v1/integrations/calendar/callback`
**Summary**: Calendar Oauth Callback  

**Parameters**:
- `code` (query, string, required) — Authorization code from Google
- `state` (query, string, required) — Fernet-encrypted state token for CSRF validation

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/calendar/conflicts`
**Summary**: List Conflicts  
**Auth**: Required  

**Parameters**:
- `status` (query, string, optional, default: pending)
- `cursor` (query, , optional)
- `limit` (query, integer, optional, default: 20)

**Response 200**: `ConflictListResponse`
```json
{
  "conflicts": [
    {
      "id": "...",
      "conflict_type": "...",
      "job_id": "...",
      "job_title": "...",
      "scheduled_start_at": "...",
      "urgency_score": "...",
      "pilot_modified_at": "...",
      "external_modified_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "total_pending": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/calendar/conflicts/test`
**Summary**: List Conflicts Test  

**Parameters**:
- `status` (query, string, optional, default: pending)
- `cursor` (query, , optional)
- `limit` (query, integer, optional, default: 20)

**Response 200**: `ConflictListResponse`
```json
{
  "conflicts": [
    {
      "id": "...",
      "conflict_type": "...",
      "job_id": "...",
      "job_title": "...",
      "scheduled_start_at": "...",
      "urgency_score": "...",
      "pilot_modified_at": "...",
      "external_modified_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "total_pending": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/calendar/conflicts/{conflict_id}`
**Summary**: Get Conflict Detail  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Response 200**: `ConflictDetailResponse`
```json
{
  "id": "string",
  "conflict_type": "string",
  "job_id": "string",
  "job_title": "Job Title",
  "scheduled_start_at": "Scheduled Start At",
  "urgency_score": "Urgency Score",
  "pilot_modified_by_user_id": "Pilot Modified By User Id",
  "pilot_modified_by_name": "Pilot Modified By Name"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/calendar/conflicts/{conflict_id}/resolve`
**Summary**: Resolve Conflict  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `ConflictResolveRequest`
```json
{
  "resolution": "string",
  "expected_pilot_modified_at": "string",
  "expected_external_modified_at": "string"
}
```

**Response 200**: `ConflictResolveResponse`
```json
{
  "id": "string",
  "resolution": "string",
  "resolved_at": "string",
  "resolved_by_user_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/calendar/conflicts/{conflict_id}/resolve/test`
**Summary**: Resolve Conflict Test  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `ConflictResolveRequest`
```json
{
  "resolution": "string",
  "expected_pilot_modified_at": "string",
  "expected_external_modified_at": "string"
}
```

**Response 200**: `ConflictResolveResponse`
```json
{
  "id": "string",
  "resolution": "string",
  "resolved_at": "string",
  "resolved_by_user_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/calendar/conflicts/{conflict_id}/test`
**Summary**: Get Conflict Detail Test  

**Parameters**:
- `conflict_id` (path, string, required)

**Response 200**: `ConflictDetailResponse`
```json
{
  "id": "string",
  "conflict_type": "string",
  "job_id": "string",
  "job_title": "Job Title",
  "scheduled_start_at": "Scheduled Start At",
  "urgency_score": "Urgency Score",
  "pilot_modified_by_user_id": "Pilot Modified By User Id",
  "pilot_modified_by_name": "Pilot Modified By Name"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/integrations/calendar/disconnect`
**Summary**: Disconnect Calendar  
**Auth**: Required  

**Response 200**: `Response Disconnect Calendar Api V1 Integrations Calendar Disconnect Delete`

---

#### `DELETE /api/v1/integrations/calendar/disconnect/test`
**Summary**: Disconnect Calendar Test  

**Response 200**: `Response Disconnect Calendar Test Api V1 Integrations Calendar Disconnect Test Delete`

---

#### `GET /api/v1/integrations/calendar/status`
**Summary**: Get Calendar Status  
**Auth**: Required  

**Response 200**: `CalendarConnectionStatus`
```json
{
  "is_connected": false,
  "provider_code": "Provider Code",
  "sync_status": "Sync Status",
  "connection_status": "Connection Status",
  "connected_at": "Connected At",
  "token_expires_at": "Token Expires At",
  "last_sync_at": "Last Sync At",
  "last_successful_sync_at": "Last Successful Sync At"
}
```

---

#### `GET /api/v1/integrations/calendar/status/test`
**Summary**: Get Calendar Status Test  

**Response 200**: `CalendarConnectionStatus`
```json
{
  "is_connected": false,
  "provider_code": "Provider Code",
  "sync_status": "Sync Status",
  "connection_status": "Connection Status",
  "connected_at": "Connected At",
  "token_expires_at": "Token Expires At",
  "last_sync_at": "Last Sync At",
  "last_successful_sync_at": "Last Successful Sync At"
}
```

---

#### `GET /api/v1/integrations/quickbooks/callback`
**Summary**: Qbo Oauth Callback  

**Parameters**:
- `code` (query, string, required) — Authorization code from QuickBooks
- `state` (query, string, required) — State token for CSRF validation
- `realmId` (query, string, required) — QuickBooks Company ID

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts`
**Summary**: List Quickbooks Conflicts  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 20)
- `status` (query, , optional)

**Response 200**: `Response List Quickbooks Conflicts Api V1 Integrations Quickbooks Conflicts Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "app_service_id": "string",
    "entity_type_code": "string",
    "entity_id": "string",
    "external_id": "string",
    "status": "string",
    "internal_payload": {}
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/b8`
**Summary**: A49: List QB conflicts with diff summary  
**Auth**: Required  

**Parameters**:
- `entity_type` (query, , optional)
- `status_filter` (query, string, optional, default: pending)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `QbConflictListResponse`
```json
{
  "items": [
    {
      "conflict_id": "...",
      "entity_type": "...",
      "entity_identifier": "...",
      "entity_summary": "...",
      "master_direction": "...",
      "pilot_change_summary": "...",
      "qb_change_summary": "...",
      "detected_at": "..."
    }
  ],
  "total": 0,
  "offset": 0,
  "limit": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/b8/history`
**Summary**: A49: QB conflict history archive  
**Auth**: Required  

**Parameters**:
- `entity_type` (query, , optional)
- `resolved_at_after` (query, , optional)
- `resolved_at_before` (query, , optional)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `QbConflictHistoryResponse`
```json
{
  "items": [
    {
      "conflict_id": "...",
      "entity_type": "...",
      "entity_identifier": "...",
      "detected_at": "...",
      "resolved_at": "...",
      "resolver_user_id": "...",
      "resolution_action": "...",
      "status": "..."
    }
  ],
  "total": 0,
  "offset": 0,
  "limit": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/b8/history/test`
**Summary**: [TEST] A49: QB conflict history (no JWT)  

**Parameters**:
- `entity_type` (query, , optional)
- `resolved_at_after` (query, , optional)
- `resolved_at_before` (query, , optional)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `QbConflictHistoryResponse`
```json
{
  "items": [
    {
      "conflict_id": "...",
      "entity_type": "...",
      "entity_identifier": "...",
      "detected_at": "...",
      "resolved_at": "...",
      "resolver_user_id": "...",
      "resolution_action": "...",
      "status": "..."
    }
  ],
  "total": 0,
  "offset": 0,
  "limit": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/b8/test`
**Summary**: [TEST] A49: List QB conflicts with diff summary (no JWT)  

**Parameters**:
- `entity_type` (query, , optional)
- `status_filter` (query, string, optional, default: pending)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `QbConflictListResponse`
```json
{
  "items": [
    {
      "conflict_id": "...",
      "entity_type": "...",
      "entity_identifier": "...",
      "entity_summary": "...",
      "master_direction": "...",
      "pilot_change_summary": "...",
      "qb_change_summary": "...",
      "detected_at": "..."
    }
  ],
  "total": 0,
  "offset": 0,
  "limit": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/b8/{conflict_id}`
**Summary**: A49: QB conflict detail with full diff payload  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Response 200**: `QbConflictDetailResponse`
```json
{
  "conflict_id": "string",
  "entity_type": "string",
  "base_snapshot": {},
  "pilot_snapshot": {},
  "qb_snapshot": {},
  "field_diffs": [
    {}
  ],
  "master_direction": "string",
  "master_recommended_action": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/quickbooks/conflicts/b8/{conflict_id}/resolve`
**Summary**: A50: Resolve QB conflict  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `QbConflictResolveRequest`
```json
{
  "resolution": "string",
  "expected_pilot_modified_at": "Expected Pilot Modified At",
  "expected_qb_modified_at": "Expected Qb Modified At"
}
```

**Response 200**: `QbConflictResolveResponse`
```json
{
  "committed": false,
  "resolution_outcome": "string",
  "post_commit_state": "Post Commit State",
  "push_to_other_side_dispatched": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/quickbooks/conflicts/b8/{conflict_id}/resolve/test`
**Summary**: [TEST] A50: Resolve QB conflict (no JWT)  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `QbConflictResolveRequest`
```json
{
  "resolution": "string",
  "expected_pilot_modified_at": "Expected Pilot Modified At",
  "expected_qb_modified_at": "Expected Qb Modified At"
}
```

**Response 200**: `QbConflictResolveResponse`
```json
{
  "committed": false,
  "resolution_outcome": "string",
  "post_commit_state": "Post Commit State",
  "push_to_other_side_dispatched": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/b8/{conflict_id}/test`
**Summary**: [TEST] A49: QB conflict detail (no JWT)  

**Parameters**:
- `conflict_id` (path, string, required)

**Response 200**: `QbConflictDetailResponse`
```json
{
  "conflict_id": "string",
  "entity_type": "string",
  "base_snapshot": {},
  "pilot_snapshot": {},
  "qb_snapshot": {},
  "field_diffs": [
    {}
  ],
  "master_direction": "string",
  "master_recommended_action": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/test`
**Summary**: List Quickbooks Conflicts Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 20)
- `status` (query, , optional)

**Response 200**: `Response List Quickbooks Conflicts Test Api V1 Integrations Quickbooks Conflicts Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "app_service_id": "string",
    "entity_type_code": "string",
    "entity_id": "string",
    "external_id": "string",
    "status": "string",
    "internal_payload": {}
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/quickbooks/conflicts/{conflict_id}/resolve`
**Summary**: Resolve Quickbooks Conflict  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `ConflictResolutionRequest`
```json
{
  "strategy": "string",
  "merged_payload": "Merged Payload",
  "notes": "Notes"
}
```

**Response 200**: `Response Resolve Quickbooks Conflict Api V1 Integrations Quickbooks Conflicts  Conflict Id  Resolve Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/quickbooks/conflicts/{conflict_id}/resolve/test`
**Summary**: Resolve Quickbooks Conflict Test  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `ConflictResolutionRequest`
```json
{
  "strategy": "string",
  "merged_payload": "Merged Payload",
  "notes": "Notes"
}
```

**Response 200**: `Response Resolve Quickbooks Conflict Test Api V1 Integrations Quickbooks Conflicts  Conflict Id  Resolve Test Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/integrations/quickbooks/connect`
**Summary**: Initiate Qbo Oauth  
**Auth**: Required  

**Response 200**: Successful Response

---

#### `GET /api/v1/integrations/quickbooks/connect/test`
**Summary**: Initiate Qbo Oauth Test  

**Response 200**: Successful Response

---

#### `DELETE /api/v1/integrations/quickbooks/disconnect`
**Summary**: Disconnect Qbo  
**Auth**: Required  

**Response 200**: `Response Disconnect Qbo Api V1 Integrations Quickbooks Disconnect Delete`

---

#### `DELETE /api/v1/integrations/quickbooks/disconnect/test`
**Summary**: Disconnect Qbo Test  

**Response 200**: `Response Disconnect Qbo Test Api V1 Integrations Quickbooks Disconnect Test Delete`

---

#### `POST /api/v1/integrations/quickbooks/refresh`
**Summary**: Refresh Qbo Token  
**Auth**: Required  

**Response 200**: `Response Refresh Qbo Token Api V1 Integrations Quickbooks Refresh Post`

---

#### `POST /api/v1/integrations/quickbooks/refresh/test`
**Summary**: Refresh Qbo Token Test  

**Response 200**: `Response Refresh Qbo Token Test Api V1 Integrations Quickbooks Refresh Test Post`

---

#### `GET /api/v1/integrations/quickbooks/status`
**Summary**: Get Qbo Connection Status  
**Auth**: Required  

**Response 200**: `QuickBooksConnectionStatus`
```json
{
  "is_connected": false,
  "realm_id": "Realm Id",
  "company_name": "Company Name",
  "connected_at": "Connected At",
  "expires_at": "Expires At",
  "connection_status": "string"
}
```

---

#### `GET /api/v1/integrations/quickbooks/status/test`
**Summary**: Get Qbo Connection Status Test  

**Response 200**: `QuickBooksConnectionStatus`
```json
{
  "is_connected": false,
  "realm_id": "Realm Id",
  "company_name": "Company Name",
  "connected_at": "Connected At",
  "expires_at": "Expires At",
  "connection_status": "string"
}
```

---

#### `POST /api/v1/integrations/quickbooks/sync/customer/{customer_id}/test`
**Summary**: Sync Customer To Qb Test  

**Parameters**:
- `customer_id` (path, string, required)

**Response 200**: `Response Sync Customer To Qb Test Api V1 Integrations Quickbooks Sync Customer  Customer Id  Test Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/integrations/quickbooks/sync/customers/test`
**Summary**: Sync Customers From Qb Test  

**Response 200**: `Response Sync Customers From Qb Test Api V1 Integrations Quickbooks Sync Customers Test Post`

---

#### `GET /api/v1/integrations/quickbooks/sync/status/test`
**Summary**: Get Sync Status Test  

**Response 200**: `Response Get Sync Status Test Api V1 Integrations Quickbooks Sync Status Test Get`

---

#### `GET /api/v1/integrations/sync-dashboard/`
**Summary**: Get Sync Dashboard  
**Auth**: Required  

**Response 200**: `SyncDashboardResponse`
```json
{
  "quickbooks_connected": false,
  "last_sync_at": "Last Sync At",
  "total_customers_mapped": 0,
  "requires_attention_count": 0
}
```

---

#### `GET /api/v1/integrations/sync-dashboard/test`
**Summary**: Get Sync Dashboard Test  

**Response 200**: `SyncDashboardResponse`
```json
{
  "quickbooks_connected": false,
  "last_sync_at": "Last Sync At",
  "total_customers_mapped": 0,
  "requires_attention_count": 0
}
```

---

### invoices

#### `GET /api/v1/invoices/`
**Summary**: List Invoices  
**Auth**: Required  

**Parameters**:
- `status` (query, , optional)
- `due_before` (query, , optional)
- `due_after` (query, , optional)
- `overdue` (query, boolean, optional, default: False) — SD-06B: Filter to only overdue invoices (due_at < now, status not in paid/void/writeoff)
- `customer_search` (query, , optional)
- `issued_from` (query, , optional)
- `issued_to` (query, , optional)
- `customer_id` (query, , optional) — Filter invoices by exact customer UUID
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `InvoiceListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "invoice_number": "...",
      "customer_id": "...",
      "customer_name": "...",
      "site_id": "...",
      "status_id": "...",
      "status_code": "...",
      "issued_at": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/`
**Summary**: Create Invoice  
**Auth**: Required  

**Request body**: `InvoiceCreate`
```json
{
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "Customer Id",
  "site_id": "Site Id",
  "line_items": "Line Items",
  "customer_notes": "Customer Notes",
  "terms_and_conditions": "Terms And Conditions",
  "due_at": "Due At"
}
```

**Response 201**: `InvoiceResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_number": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "string",
  "quote_id": "Quote Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/invoices/test`
**Summary**: List Invoices Test  

**Parameters**:
- `status` (query, , optional)
- `due_before` (query, , optional)
- `due_after` (query, , optional)
- `customer_search` (query, , optional)
- `issued_from` (query, , optional)
- `issued_to` (query, , optional)
- `customer_id` (query, , optional) — Filter invoices by exact customer UUID
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `InvoiceListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "invoice_number": "...",
      "customer_id": "...",
      "customer_name": "...",
      "site_id": "...",
      "status_id": "...",
      "status_code": "...",
      "issued_at": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/test`
**Summary**: Create Invoice Test  

**Request body**: `InvoiceCreate`
```json
{
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "Customer Id",
  "site_id": "Site Id",
  "line_items": "Line Items",
  "customer_notes": "Customer Notes",
  "terms_and_conditions": "Terms And Conditions",
  "due_at": "Due At"
}
```

**Response 201**: `InvoiceResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_number": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "string",
  "quote_id": "Quote Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/invoices/{invoice_id}`
**Summary**: Get Invoice  
**Auth**: Required  

**Parameters**:
- `invoice_id` (path, string, required)

**Response 200**: `InvoiceResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_number": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "string",
  "quote_id": "Quote Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{invoice_id}/record-payment`
**Summary**: Record Payment  
**Auth**: Required  

**Parameters**:
- `invoice_id` (path, string, required)

**Request body**: `PaymentRecordRequest`
```json
{
  "amount_cents": 0,
  "paid_via": "string",
  "payment_method_id": "string",
  "payment_status_id": "string",
  "paid_at": "Paid At",
  "reference": "Reference",
  "idempotency_key": "Idempotency Key",
  "comment": "Comment"
}
```

**Response 201**: `PaymentResponse`
```json
{
  "id": "string",
  "invoice_id": "string",
  "tenant_id": "string",
  "amount_cents": 0,
  "paid_via": "string",
  "balance_due_cents": 0,
  "amount_variance_cents": "Amount Variance Cents",
  "status_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{invoice_id}/record-payment/test`
**Summary**: Record Payment Test  

**Parameters**:
- `invoice_id` (path, string, required)

**Request body**: `PaymentRecordRequest`
```json
{
  "amount_cents": 0,
  "paid_via": "string",
  "payment_method_id": "string",
  "payment_status_id": "string",
  "paid_at": "Paid At",
  "reference": "Reference",
  "idempotency_key": "Idempotency Key",
  "comment": "Comment"
}
```

**Response 201**: `PaymentResponse`
```json
{
  "id": "string",
  "invoice_id": "string",
  "tenant_id": "string",
  "amount_cents": 0,
  "paid_via": "string",
  "balance_due_cents": 0,
  "amount_variance_cents": "Amount Variance Cents",
  "status_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{invoice_id}/send`
**Summary**: Send Invoice  
**Auth**: Required  

**Parameters**:
- `invoice_id` (path, string, required)

**Request body**: `InvoiceSendRequest`
```json
{
  "contact_id": "Contact Id",
  "expires_in_days": "Expires In Days",
  "max_uses": 0
}
```

**Response 201**: `InvoicePublicLinkResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_id": "string",
  "contact_id": "Contact Id",
  "signed_token": "string",
  "expires_at": "Expires At",
  "max_uses": 0,
  "used_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{invoice_id}/send/test`
**Summary**: Send Invoice Test  

**Parameters**:
- `invoice_id` (path, string, required)

**Request body**: `InvoiceSendRequest`
```json
{
  "contact_id": "Contact Id",
  "expires_in_days": "Expires In Days",
  "max_uses": 0
}
```

**Response 201**: `InvoicePublicLinkResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_id": "string",
  "contact_id": "Contact Id",
  "signed_token": "string",
  "expires_at": "Expires At",
  "max_uses": 0,
  "used_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/invoices/{invoice_id}/signoff`
**Summary**: Get Signoff  
**Auth**: Required  

**Parameters**:
- `invoice_id` (path, string, required)

**Response 200**: `InvoiceSignoffDetailResponse`
```json
{
  "signoff": "object",
  "superseded_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{invoice_id}/signoff`
**Summary**: Create Signoff  
**Auth**: Required  

**Parameters**:
- `invoice_id` (path, string, required)
- `Idempotency-Key` (header, , optional)

**Request body**: `InvoiceSignoffCreateRequest`
```json
{
  "signed_by_name": "string",
  "terms_acknowledged": false,
  "signature_png_base64": "string",
  "client_capture_at": "Client Capture At"
}
```

**Response 200**: `InvoiceSignoffResponse`
```json
{
  "signoff_id": "string",
  "invoice_id": "string",
  "signed_by_name": "string",
  "signed_at": "string",
  "client_capture_at": "Client Capture At",
  "captured_by_user_id": "string",
  "signature_url": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/invoices/{invoice_id}/signoff/test`
**Summary**: Get Signoff Test  

**Parameters**:
- `invoice_id` (path, string, required)

**Response 200**: `InvoiceSignoffDetailResponse`
```json
{
  "signoff": "object",
  "superseded_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{invoice_id}/signoff/test`
**Summary**: Create Signoff Test  

**Parameters**:
- `invoice_id` (path, string, required)
- `Idempotency-Key` (header, , optional)

**Request body**: `InvoiceSignoffCreateRequest`
```json
{
  "signed_by_name": "string",
  "terms_acknowledged": false,
  "signature_png_base64": "string",
  "client_capture_at": "Client Capture At"
}
```

**Response 200**: `InvoiceSignoffResponse`
```json
{
  "signoff_id": "string",
  "invoice_id": "string",
  "signed_by_name": "string",
  "signed_at": "string",
  "client_capture_at": "Client Capture At",
  "captured_by_user_id": "string",
  "signature_url": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/invoices/{invoice_id}/test`
**Summary**: Get Invoice Test  

**Parameters**:
- `invoice_id` (path, string, required)

**Response 200**: `InvoiceResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_number": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "string",
  "quote_id": "Quote Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{payment_id}/resolve-variance`
**Summary**: Resolve Variance  
**Auth**: Required  

**Parameters**:
- `payment_id` (path, string, required)

**Request body**: `ResolveVarianceRequest`
```json
{
  "resolution": "string",
  "note": "Note"
}
```

**Response 200**: `PaymentResponse`
```json
{
  "id": "string",
  "invoice_id": "string",
  "tenant_id": "string",
  "amount_cents": 0,
  "paid_via": "string",
  "balance_due_cents": 0,
  "amount_variance_cents": "Amount Variance Cents",
  "status_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/invoices/{payment_id}/resolve-variance/test`
**Summary**: Resolve Variance Test  

**Parameters**:
- `payment_id` (path, string, required)

**Request body**: `ResolveVarianceRequest`
```json
{
  "resolution": "string",
  "note": "Note"
}
```

**Response 200**: `PaymentResponse`
```json
{
  "id": "string",
  "invoice_id": "string",
  "tenant_id": "string",
  "amount_cents": 0,
  "paid_via": "string",
  "balance_due_cents": 0,
  "amount_variance_cents": "Amount Variance Cents",
  "status_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### job-expense-categories

#### `GET /api/v1/job-expense-categories`
**Summary**: List job expense categories for the tenant  
**Auth**: Required  

**Response 200**: `JobExpenseCategoriesResponse`
```json
{
  "categories": [
    {
      "code": "...",
      "name": "...",
      "is_default": "..."
    }
  ]
}
```

---

#### `GET /api/v1/job-expense-categories/test`
**Summary**: [TEST] List job expense categories (no JWT)  

**Response 200**: `JobExpenseCategoriesResponse`
```json
{
  "categories": [
    {
      "code": "...",
      "name": "...",
      "is_default": "..."
    }
  ]
}
```

---

### job-recurrence-rules

#### `GET /api/v1/job-recurrence-rules/`
**Summary**: List Recurrence Rules  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 50)

**Response 200**: `RecurrenceRuleListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "pattern": "...",
      "interval_count": "...",
      "customer_name": "...",
      "site_address": "...",
      "next_job_at": "...",
      "occurrences_created": "...",
      "is_active": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/job-recurrence-rules/`
**Summary**: Create Recurrence Rule  
**Auth**: Required  

**Request body**: `RecurrenceRuleCreate`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On",
  "max_occurrences": "Max Occurrences",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 201**: `RecurrenceRuleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/job-recurrence-rules/test`
**Summary**: List Recurrence Rules Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 50)

**Response 200**: `RecurrenceRuleListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "pattern": "...",
      "interval_count": "...",
      "customer_name": "...",
      "site_address": "...",
      "next_job_at": "...",
      "occurrences_created": "...",
      "is_active": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/job-recurrence-rules/test`
**Summary**: Create Recurrence Rule Test  

**Request body**: `RecurrenceRuleCreate`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On",
  "max_occurrences": "Max Occurrences",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 201**: `RecurrenceRuleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/job-recurrence-rules/{rule_id}`
**Summary**: Get Recurrence Rule  
**Auth**: Required  

**Parameters**:
- `rule_id` (path, string, required)

**Response 200**: `RecurrenceRuleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/job-recurrence-rules/{rule_id}`
**Summary**: Update Recurrence Rule  
**Auth**: Required  

**Parameters**:
- `rule_id` (path, string, required)

**Request body**: `RecurrenceRuleUpdate`
```json
{
  "is_active": "Is Active",
  "ends_on": "Ends On",
  "max_occurrences": "Max Occurrences",
  "default_tech_user_id": "Default Tech User Id",
  "notes_template": "Notes Template",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 200**: `RecurrenceRuleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/job-recurrence-rules/{rule_id}`
**Summary**: Delete Recurrence Rule  
**Auth**: Required  

**Parameters**:
- `rule_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/job-recurrence-rules/{rule_id}/test`
**Summary**: Get Recurrence Rule Test  

**Parameters**:
- `rule_id` (path, string, required)

**Response 200**: `RecurrenceRuleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/job-recurrence-rules/{rule_id}/test`
**Summary**: Update Recurrence Rule Test  

**Parameters**:
- `rule_id` (path, string, required)

**Request body**: `RecurrenceRuleUpdate`
```json
{
  "is_active": "Is Active",
  "ends_on": "Ends On",
  "max_occurrences": "Max Occurrences",
  "default_tech_user_id": "Default Tech User Id",
  "notes_template": "Notes Template",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 200**: `RecurrenceRuleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "pattern": "string",
  "interval_count": 0,
  "starts_on": "string",
  "ends_on": "Ends On"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/job-recurrence-rules/{rule_id}/test`
**Summary**: Delete Recurrence Rule Test  

**Parameters**:
- `rule_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### job-types

#### `GET /api/v1/job-types`
**Summary**: List Job Types  
**Auth**: Required  

**Response 200**: `Response List Job Types Api V1 Job Types Get`
```json
[
  {
    "id": "string",
    "code": "string",
    "label": "string",
    "sort_order": 0,
    "is_active": false,
    "is_tenant_override": false
  }
]
```

---

#### `GET /api/v1/job-types/test`
**Summary**: List Job Types Test  

**Response 200**: `Response List Job Types Test Api V1 Job Types Test Get`
```json
[
  {
    "id": "string",
    "code": "string",
    "label": "string",
    "sort_order": 0,
    "is_active": false,
    "is_tenant_override": false
  }
]
```

---

### jobs

#### `GET /api/v1/jobs/`
**Summary**: List Jobs  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `tech_id` (query, , optional) — Filter by assigned tech user UUID
- `scheduled_date` (query, , optional) — Filter by scheduled date (YYYY-MM-DD) — dispatch board compat
- `status` (query, , optional) — Filter by job status code
- `customer_search` (query, , optional) — Case-insensitive search on customer name
- `scheduled_from` (query, , optional) — Filter jobs starting on or after this datetime
- `scheduled_to` (query, , optional) — Filter jobs starting on or before this datetime
- `customer_id` (query, , optional) — Filter jobs by exact customer UUID

**Response 200**: `PaginatedJobListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "site_id": "...",
      "status_id": "...",
      "status_code": "...",
      "customer_name": "...",
      "job_number": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/`
**Summary**: Create Job  
**Auth**: Required  

**Request body**: `JobCreate`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "quote_id": "Quote Id",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes",
  "external_calendar_event_id": "External Calendar Event Id",
  "priority": "Priority"
}
```

**Response 201**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/test`
**Summary**: List Jobs Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `tech_id` (query, , optional) — Filter by assigned tech user UUID
- `scheduled_date` (query, , optional) — Filter by scheduled date (YYYY-MM-DD)
- `status` (query, , optional) — Filter by job status code (e.g. draft, scheduled)
- `customer_search` (query, , optional) — Case-insensitive search on customer name
- `scheduled_from` (query, , optional) — Filter jobs starting on or after this datetime
- `scheduled_to` (query, , optional) — Filter jobs starting on or before this datetime
- `customer_id` (query, , optional) — Filter jobs by exact customer UUID

**Response 200**: `PaginatedJobListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "site_id": "...",
      "status_id": "...",
      "status_code": "...",
      "customer_name": "...",
      "job_number": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/test`
**Summary**: Create Job Test  

**Request body**: `JobCreate`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "quote_id": "Quote Id",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes",
  "external_calendar_event_id": "External Calendar Event Id",
  "priority": "Priority"
}
```

**Response 201**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}`
**Summary**: Get Job  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/jobs/{job_id}`
**Summary**: Update Job  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobUpdate`
```json
{
  "customer_id": "Customer Id",
  "site_id": "Site Id",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes",
  "priority": "Priority",
  "job_type_id": "Job Type Id",
  "title": "Title"
}
```

**Response 200**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/billable-items`
**Summary**: Get Job Billable Items  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `BillableItemsResponse`
```json
{
  "job_id": "string",
  "job_number": "Job Number",
  "customer_name": "Customer Name",
  "time_entries": [
    {
      "id": "...",
      "user_id": "...",
      "tech_name": "...",
      "started_at": "...",
      "ended_at": "...",
      "hours": "...",
      "hourly_rate_cents": "...",
      "total_cost_cents": "..."
    }
  ],
  "expenses": [
    {
      "id": "...",
      "description": "...",
      "cost_cents": "...",
      "billable_cents": "...",
      "is_billable": "...",
      "is_already_invoiced": "...",
      "incurred_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/billable-items/test`
**Summary**: Get Job Billable Items Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `BillableItemsResponse`
```json
{
  "job_id": "string",
  "job_number": "Job Number",
  "customer_name": "Customer Name",
  "time_entries": [
    {
      "id": "...",
      "user_id": "...",
      "tech_name": "...",
      "started_at": "...",
      "ended_at": "...",
      "hours": "...",
      "hourly_rate_cents": "...",
      "total_cost_cents": "..."
    }
  ],
  "expenses": [
    {
      "id": "...",
      "description": "...",
      "cost_cents": "...",
      "billable_cents": "...",
      "is_billable": "...",
      "is_already_invoiced": "...",
      "incurred_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/change-orders`
**Summary**: List Change Orders  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Change Orders Api V1 Jobs  Job Id  Change Orders Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "description": "string",
    "subtotal_cents": 0,
    "tax_cents": 0,
    "total_cents": 0,
    "is_active": false
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/change-orders`
**Summary**: Create Change Order  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `ChangeOrderCreate`
```json
{
  "description": "string",
  "client_capture_at": "Client Capture At"
}
```

**Response 201**: `ChangeOrderResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "description": "string",
  "subtotal_cents": 0,
  "tax_cents": 0,
  "total_cents": 0,
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/change-orders/test`
**Summary**: List Change Orders Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Change Orders Test Api V1 Jobs  Job Id  Change Orders Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "description": "string",
    "subtotal_cents": 0,
    "tax_cents": 0,
    "total_cents": 0,
    "is_active": false
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/change-orders/test`
**Summary**: Create Change Order Test  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `ChangeOrderCreate`
```json
{
  "description": "string",
  "client_capture_at": "Client Capture At"
}
```

**Response 201**: `ChangeOrderResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "description": "string",
  "subtotal_cents": 0,
  "tax_cents": 0,
  "total_cents": 0,
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/change-orders/{co_id}`
**Summary**: Get Change Order  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Response 200**: `ChangeOrderResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "description": "string",
  "subtotal_cents": 0,
  "tax_cents": 0,
  "total_cents": 0,
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/jobs/{job_id}/change-orders/{co_id}`
**Summary**: Update Change Order  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Request body**: `ChangeOrderUpdate`
```json
{
  "description": "Description",
  "is_active": "Is Active"
}
```

**Response 200**: `ChangeOrderResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "description": "string",
  "subtotal_cents": 0,
  "tax_cents": 0,
  "total_cents": 0,
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/jobs/{job_id}/change-orders/{co_id}`
**Summary**: Delete Change Order  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/change-orders/{co_id}/lines`
**Summary**: List Change Order Lines  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Response 200**: `Response List Change Order Lines Api V1 Jobs  Job Id  Change Orders  Co Id  Lines Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "change_order_id": "string",
    "position": 0,
    "qco_line_type_id": "string",
    "description": "string",
    "quantity": 0.0,
    "unit": "Unit"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/change-orders/{co_id}/lines`
**Summary**: Create Change Order Line  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Request body**: `ChangeOrderLineCreate`
```json
{
  "position": 0,
  "qco_line_type_id": "string",
  "description": "string",
  "quantity": 0.0,
  "unit_price_cents": 0,
  "unit": "Unit",
  "pricebook_item_id": "Pricebook Item Id",
  "supplier_id": "Supplier Id"
}
```

**Response 201**: `ChangeOrderLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "change_order_id": "string",
  "position": 0,
  "qco_line_type_id": "string",
  "description": "string",
  "quantity": 0.0,
  "unit": "Unit"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/change-orders/{co_id}/lines/test`
**Summary**: List Change Order Lines Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Response 200**: `Response List Change Order Lines Test Api V1 Jobs  Job Id  Change Orders  Co Id  Lines Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "change_order_id": "string",
    "position": 0,
    "qco_line_type_id": "string",
    "description": "string",
    "quantity": 0.0,
    "unit": "Unit"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/change-orders/{co_id}/lines/test`
**Summary**: Create Change Order Line Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Request body**: `ChangeOrderLineCreate`
```json
{
  "position": 0,
  "qco_line_type_id": "string",
  "description": "string",
  "quantity": 0.0,
  "unit_price_cents": 0,
  "unit": "Unit",
  "pricebook_item_id": "Pricebook Item Id",
  "supplier_id": "Supplier Id"
}
```

**Response 201**: `ChangeOrderLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "change_order_id": "string",
  "position": 0,
  "qco_line_type_id": "string",
  "description": "string",
  "quantity": 0.0,
  "unit": "Unit"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/jobs/{job_id}/change-orders/{co_id}/lines/{line_id}`
**Summary**: Update Change Order Line  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)
- `line_id` (path, string, required)

**Request body**: `ChangeOrderLineUpdate`
```json
{
  "position": "Position",
  "description": "Description",
  "quantity": "Quantity",
  "unit_price_cents": "Unit Price Cents",
  "unit": "Unit",
  "is_active": "Is Active"
}
```

**Response 200**: `ChangeOrderLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "change_order_id": "string",
  "position": 0,
  "qco_line_type_id": "string",
  "description": "string",
  "quantity": 0.0,
  "unit": "Unit"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/jobs/{job_id}/change-orders/{co_id}/lines/{line_id}`
**Summary**: Delete Change Order Line  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)
- `line_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/jobs/{job_id}/change-orders/{co_id}/lines/{line_id}/test`
**Summary**: Update Change Order Line Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)
- `line_id` (path, string, required)

**Request body**: `ChangeOrderLineUpdate`
```json
{
  "position": "Position",
  "description": "Description",
  "quantity": "Quantity",
  "unit_price_cents": "Unit Price Cents",
  "unit": "Unit",
  "is_active": "Is Active"
}
```

**Response 200**: `ChangeOrderLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "change_order_id": "string",
  "position": 0,
  "qco_line_type_id": "string",
  "description": "string",
  "quantity": 0.0,
  "unit": "Unit"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/jobs/{job_id}/change-orders/{co_id}/lines/{line_id}/test`
**Summary**: Delete Change Order Line Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)
- `line_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/change-orders/{co_id}/test`
**Summary**: Get Change Order Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Response 200**: `ChangeOrderResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "description": "string",
  "subtotal_cents": 0,
  "tax_cents": 0,
  "total_cents": 0,
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/jobs/{job_id}/change-orders/{co_id}/test`
**Summary**: Update Change Order Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Request body**: `ChangeOrderUpdate`
```json
{
  "description": "Description",
  "is_active": "Is Active"
}
```

**Response 200**: `ChangeOrderResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "description": "string",
  "subtotal_cents": 0,
  "tax_cents": 0,
  "total_cents": 0,
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/jobs/{job_id}/change-orders/{co_id}/test`
**Summary**: Delete Change Order Test  

**Parameters**:
- `job_id` (path, string, required)
- `co_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/expenses`
**Summary**: List Job Expenses  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Job Expenses Api V1 Jobs  Job Id  Expenses Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "job_expense_category_code": "string",
    "description": "string",
    "vendor_name": "Vendor Name",
    "incurred_at": "string",
    "cost_cents": 0
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/expenses`
**Summary**: Create Job Expense  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobExpenseCreate`
```json
{
  "job_expense_category_code": "string",
  "description": "string",
  "vendor_name": "Vendor Name",
  "incurred_at": "string",
  "cost_cents": 0,
  "is_billable": false,
  "client_capture_at": "Client Capture At"
}
```

**Response 201**: `JobExpenseResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "job_expense_category_code": "string",
  "description": "string",
  "vendor_name": "Vendor Name",
  "incurred_at": "string",
  "cost_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/expenses/test`
**Summary**: List Job Expenses Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Job Expenses Test Api V1 Jobs  Job Id  Expenses Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "job_expense_category_code": "string",
    "description": "string",
    "vendor_name": "Vendor Name",
    "incurred_at": "string",
    "cost_cents": 0
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/expenses/test`
**Summary**: Create Job Expense Test  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobExpenseCreate`
```json
{
  "job_expense_category_code": "string",
  "description": "string",
  "vendor_name": "Vendor Name",
  "incurred_at": "string",
  "cost_cents": 0,
  "is_billable": false,
  "client_capture_at": "Client Capture At"
}
```

**Response 201**: `JobExpenseResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "job_expense_category_code": "string",
  "description": "string",
  "vendor_name": "Vendor Name",
  "incurred_at": "string",
  "cost_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/loto-confirmations`
**Summary**: List Loto Confirmations  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Loto Confirmations Api V1 Jobs  Job Id  Loto Confirmations Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "user_id": "string",
    "confirmed_at": "string",
    "client_capture_at": "Client Capture At",
    "server_received_at": "Server Received At",
    "is_active": false
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/loto-confirmations`
**Summary**: Create Loto Confirmation  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `LotoConfirmationCreate`
```json
{
  "confirmed_at": "string",
  "client_capture_at": "Client Capture At",
  "idempotency_uuid": "string"
}
```

**Response 201**: `LotoConfirmationRead`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "user_id": "string",
  "confirmed_at": "string",
  "client_capture_at": "Client Capture At",
  "server_received_at": "Server Received At",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/loto-confirmations/test`
**Summary**: List Loto Confirmations Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Loto Confirmations Test Api V1 Jobs  Job Id  Loto Confirmations Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "user_id": "string",
    "confirmed_at": "string",
    "client_capture_at": "Client Capture At",
    "server_received_at": "Server Received At",
    "is_active": false
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/loto-confirmations/test`
**Summary**: Create Loto Confirmation Test  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `LotoConfirmationCreate`
```json
{
  "confirmed_at": "string",
  "client_capture_at": "Client Capture At",
  "idempotency_uuid": "string"
}
```

**Response 201**: `LotoConfirmationRead`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "user_id": "string",
  "confirmed_at": "string",
  "client_capture_at": "Client Capture At",
  "server_received_at": "Server Received At",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/notes`
**Summary**: Get Job Notes  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `JobNotesResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "notes": "string",
  "audio_object_key": "Audio Object Key",
  "customer_visible": false,
  "client_capture_at": "Client Capture At",
  "server_received_at": "Server Received At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/jobs/{job_id}/notes`
**Summary**: Upsert Job Notes  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobNotesUpdate`
```json
{
  "notes": "string"
}
```

**Response 200**: `JobNotesResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "notes": "string",
  "audio_object_key": "Audio Object Key",
  "customer_visible": false,
  "client_capture_at": "Client Capture At",
  "server_received_at": "Server Received At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/notes/test`
**Summary**: Get Job Notes Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `JobNotesResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "notes": "string",
  "audio_object_key": "Audio Object Key",
  "customer_visible": false,
  "client_capture_at": "Client Capture At",
  "server_received_at": "Server Received At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/jobs/{job_id}/notes/test`
**Summary**: Upsert Job Notes Test  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobNotesUpdate`
```json
{
  "notes": "string"
}
```

**Response 200**: `JobNotesResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "notes": "string",
  "audio_object_key": "Audio Object Key",
  "customer_visible": false,
  "client_capture_at": "Client Capture At",
  "server_received_at": "Server Received At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/projected-margin`
**Summary**: Get projected margin with ETC  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response Projected Margin Api V1 Jobs  Job Id  Projected Margin Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/projected-margin/test`
**Summary**: [TEST] Get projected margin — no auth required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response Projected Margin Test Api V1 Jobs  Job Id  Projected Margin Test Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/signoff-context`
**Summary**: Get Signoff Context  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `SignoffContextResponse`
```json
{
  "job_id": "string",
  "customer_display_name": "string",
  "invoices": [
    {
      "invoice_id": "...",
      "invoice_number": "...",
      "status": "...",
      "total_cents": "...",
      "balance_due_cents": "...",
      "currency": "...",
      "terms_text": "...",
      "active_signoff": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/signoff-context/test`
**Summary**: Get Signoff Context Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `SignoffContextResponse`
```json
{
  "job_id": "string",
  "customer_display_name": "string",
  "invoices": [
    {
      "invoice_id": "...",
      "invoice_number": "...",
      "status": "...",
      "total_cents": "...",
      "balance_due_cents": "...",
      "currency": "...",
      "terms_text": "...",
      "active_signoff": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/test`
**Summary**: Get Job Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/jobs/{job_id}/test`
**Summary**: Update Job Test  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobUpdate`
```json
{
  "customer_id": "Customer Id",
  "site_id": "Site Id",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes",
  "priority": "Priority",
  "job_type_id": "Job Type Id",
  "title": "Title"
}
```

**Response 200**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/time-entries`
**Summary**: List Job Time Entries  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Job Time Entries Api V1 Jobs  Job Id  Time Entries Get`
```json
[
  {
    "id": "string",
    "job_id": "string",
    "user_id": "string",
    "started_at": "string",
    "ended_at": "Ended At",
    "hours": "Hours",
    "notes": "Notes",
    "hourly_rate_cents": 0
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/time-entries`
**Summary**: Create Job Time Entry  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobTimeEntryCreate`
```json
{
  "started_at": "string",
  "ended_at": "Ended At",
  "hours": "Hours",
  "notes": "Notes",
  "hourly_rate_cents": "Hourly Rate Cents",
  "client_capture_at": "Client Capture At",
  "hours_remaining_estimate": "Hours Remaining Estimate",
  "hours_remaining_was_overridden": "Hours Remaining Was Overridden"
}
```

**Response 201**: `JobTimeEntryResponse`
```json
{
  "id": "string",
  "job_id": "string",
  "user_id": "string",
  "started_at": "string",
  "ended_at": "Ended At",
  "hours": "Hours",
  "notes": "Notes",
  "hourly_rate_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/jobs/{job_id}/time-entries/test`
**Summary**: List Job Time Entries Test  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Job Time Entries Test Api V1 Jobs  Job Id  Time Entries Test Get`
```json
[
  {
    "id": "string",
    "job_id": "string",
    "user_id": "string",
    "started_at": "string",
    "ended_at": "Ended At",
    "hours": "Hours",
    "notes": "Notes",
    "hourly_rate_cents": 0
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/jobs/{job_id}/time-entries/test`
**Summary**: Create Job Time Entry Test  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobTimeEntryCreate`
```json
{
  "started_at": "string",
  "ended_at": "Ended At",
  "hours": "Hours",
  "notes": "Notes",
  "hourly_rate_cents": "Hourly Rate Cents",
  "client_capture_at": "Client Capture At",
  "hours_remaining_estimate": "Hours Remaining Estimate",
  "hours_remaining_was_overridden": "Hours Remaining Was Overridden"
}
```

**Response 201**: `JobTimeEntryResponse`
```json
{
  "id": "string",
  "job_id": "string",
  "user_id": "string",
  "started_at": "string",
  "ended_at": "Ended At",
  "hours": "Hours",
  "notes": "Notes",
  "hourly_rate_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### marketing

#### `POST /api/v1/marketing/application`
**Summary**: Submit a job application  

**Request body**: `JobApplicationRequest`
```json
{
  "name": "string",
  "email": "string",
  "role": "string",
  "linkedin_url": "Linkedin Url",
  "portfolio_url": "Portfolio Url",
  "why_interested": "string",
  "cf_turnstile_response": "string",
  "honeypot": "Honeypot"
}
```

**Response 201**: `JobApplicationResponse`
```json
{
  "status": "string",
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/application/test`
**Summary**: [TEST] Job application submit  

**Request body**: `JobApplicationRequest`
```json
{
  "name": "string",
  "email": "string",
  "role": "string",
  "linkedin_url": "Linkedin Url",
  "portfolio_url": "Portfolio Url",
  "why_interested": "string",
  "cf_turnstile_response": "string",
  "honeypot": "Honeypot"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/contact`
**Summary**: Submit the Pilot for Trades contact form  

**Request body**: `ContactSubmissionRequest`
```json
{
  "name": "string",
  "email": "string",
  "company": "Company",
  "trade": "Trade",
  "subject": "string",
  "message": "string",
  "source_page": "Source Page",
  "cf_turnstile_response": "string"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/contact/test`
**Summary**: [TEST] Contact form submit  

**Request body**: `ContactSubmissionRequest`
```json
{
  "name": "string",
  "email": "string",
  "company": "Company",
  "trade": "Trade",
  "subject": "string",
  "message": "string",
  "source_page": "Source Page",
  "cf_turnstile_response": "string"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/newsletter`
**Summary**: Subscribe to Pilot for Trades newsletter  

**Request body**: `NewsletterSubscribeRequest`
```json
{
  "email": "string",
  "trade_interest": "Trade Interest",
  "content_preferences": "Content Preferences",
  "source": "Source",
  "utm_source": "Utm Source",
  "utm_medium": "Utm Medium",
  "utm_campaign": "Utm Campaign",
  "cf_turnstile_response": "string"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/newsletter/test`
**Summary**: [TEST] Newsletter subscribe  

**Request body**: `NewsletterSubscribeRequest`
```json
{
  "email": "string",
  "trade_interest": "Trade Interest",
  "content_preferences": "Content Preferences",
  "source": "Source",
  "utm_source": "Utm Source",
  "utm_medium": "Utm Medium",
  "utm_campaign": "Utm Campaign",
  "cf_turnstile_response": "string"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/newsletter/unsubscribe`
**Summary**: One-click newsletter unsubscribe  

**Parameters**:
- `token` (query, string, required)

**Response 200**: `NewsletterUnsubscribeResponse`
```json
{
  "status": "string",
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/waitlist`
**Summary**: Join the Pilot for Trades waitlist  

**Request body**: `WaitlistSignupRequest`
```json
{
  "email": "string",
  "name": "Name",
  "trade": "string",
  "company_size": "string",
  "state": "State",
  "notes": "Notes",
  "source": "string",
  "utm_source": "Utm Source"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/marketing/waitlist/test`
**Summary**: [TEST] Waitlist signup  

**Request body**: `WaitlistSignupRequest`
```json
{
  "email": "string",
  "name": "Name",
  "trade": "string",
  "company_size": "string",
  "state": "State",
  "notes": "Notes",
  "source": "string",
  "utm_source": "Utm Source"
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### mobile

#### `POST /api/v1/mobile/push-tokens`
**Summary**: Register or refresh a device push token  
**Auth**: Required  

**Request body**: `PushTokenRegisterRequest`
```json
{
  "device_id": "string",
  "platform": "string",
  "push_token": "string",
  "app_version": "App Version",
  "os_version": "Os Version",
  "notification_permission_granted": false
}
```

**Response 200**: `PushTokenRegisterResponse`
```json
{
  "device_id": "string",
  "registered_at": "string",
  "last_seen_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/mobile/push-tokens/test`
**Summary**: [Test] Register push token  

**Request body**: `PushTokenRegisterRequest`
```json
{
  "device_id": "string",
  "platform": "string",
  "push_token": "string",
  "app_version": "App Version",
  "os_version": "Os Version",
  "notification_permission_granted": false
}
```

**Response 200**: `PushTokenRegisterResponse`
```json
{
  "device_id": "string",
  "registered_at": "string",
  "last_seen_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/mobile/push-tokens/{device_id}`
**Summary**: Revoke a device push token  
**Auth**: Required  

**Parameters**:
- `device_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/mobile/push-tokens/{device_id}/test`
**Summary**: [Test] Revoke push token  

**Parameters**:
- `device_id` (path, string, required)

**Response 204**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/mobile/sync-sessions/{session_id}/complete`
**Summary**: Report sync session completion telemetry  
**Auth**: Required  

**Parameters**:
- `session_id` (path, string, required)

**Request body**: `SyncSessionCompleteRequest`
```json
{
  "outcome": "string",
  "items_attempted": 0,
  "items_committed": 0,
  "items_deferred": 0,
  "items_failed": 0,
  "failure_reason": "Failure Reason"
}
```

**Response 200**: `SyncSessionCompleteResponse`
```json
{
  "session_id": "string",
  "outcome": "Outcome",
  "completed_at": "Completed At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/mobile/sync-sessions/{session_id}/complete/test`
**Summary**: [Test] Complete sync session  

**Parameters**:
- `session_id` (path, string, required)

**Request body**: `SyncSessionCompleteRequest`
```json
{
  "outcome": "string",
  "items_attempted": 0,
  "items_committed": 0,
  "items_deferred": 0,
  "items_failed": 0,
  "failure_reason": "Failure Reason"
}
```

**Response 200**: `SyncSessionCompleteResponse`
```json
{
  "session_id": "string",
  "outcome": "Outcome",
  "completed_at": "Completed At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/me/devices/{device_id}/push-permission`
**Summary**: Get Push Permission  
**Auth**: Required  

**Parameters**:
- `device_id` (path, string, required)

**Response 200**: `PushPermissionResponse`
```json
{
  "device_id": "string",
  "permission_state": "string",
  "last_state_change_at": "string",
  "dismissable_banner_dismissed_at": "Dismissable Banner Dismissed At",
  "banner_should_appear": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/users/me/devices/{device_id}/push-permission`
**Summary**: Update Push Permission  
**Auth**: Required  

**Parameters**:
- `device_id` (path, string, required)

**Request body**: `PushPermissionUpdateRequest`
```json
{
  "permission_state": "string"
}
```

**Response 200**: `PushPermissionResponse`
```json
{
  "device_id": "string",
  "permission_state": "string",
  "last_state_change_at": "string",
  "dismissable_banner_dismissed_at": "Dismissable Banner Dismissed At",
  "banner_should_appear": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/test/devices/{device_id}/push-permission`
**Summary**: Get Push Permission Test  

**Parameters**:
- `device_id` (path, string, required)

**Response 200**: `PushPermissionResponse`
```json
{
  "device_id": "string",
  "permission_state": "string",
  "last_state_change_at": "string",
  "dismissable_banner_dismissed_at": "Dismissable Banner Dismissed At",
  "banner_should_appear": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/users/test/devices/{device_id}/push-permission`
**Summary**: Update Push Permission Test  

**Parameters**:
- `device_id` (path, string, required)

**Request body**: `PushPermissionUpdateRequest`
```json
{
  "permission_state": "string"
}
```

**Response 200**: `PushPermissionResponse`
```json
{
  "device_id": "string",
  "permission_state": "string",
  "last_state_change_at": "string",
  "dismissable_banner_dismissed_at": "Dismissable Banner Dismissed At",
  "banner_should_appear": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### mobile-sync

#### `GET /api/v1/mobile-sync/conflicts/{conflict_id}`
**Summary**: Get conflict detail for tech resolution  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Response 200**: `ConflictDetailResponse`
```json
{
  "conflict_id": "string",
  "operation_type": "string",
  "status": "string",
  "conflict_severity": "Conflict Severity",
  "classification_reason": "Classification Reason",
  "tech_version": "Tech Version",
  "server_version": "Server Version",
  "field_diffs": "Field Diffs"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve`
**Summary**: Resolve a tech-resolvable conflict  
**Auth**: Required  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `ConflictResolveRequest`
```json
{
  "resolution": "string",
  "expected_server_version_at": "Expected Server Version At"
}
```

**Response 200**: `ConflictResolveResponse`
```json
{
  "conflict_id": "string",
  "resolution": "string",
  "resolved_at": "string",
  "escalation_id": "Escalation Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve/test`
**Summary**: [TEST] Resolve conflict (no JWT)  

**Parameters**:
- `conflict_id` (path, string, required)

**Request body**: `ConflictResolveRequest`
```json
{
  "resolution": "string",
  "expected_server_version_at": "Expected Server Version At"
}
```

**Response 200**: `ConflictResolveResponse`
```json
{
  "conflict_id": "string",
  "resolution": "string",
  "resolved_at": "string",
  "escalation_id": "Escalation Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/mobile-sync/conflicts/{conflict_id}/test`
**Summary**: [TEST] Get conflict detail (no JWT)  

**Parameters**:
- `conflict_id` (path, string, required)

**Response 200**: `ConflictDetailResponse`
```json
{
  "conflict_id": "string",
  "operation_type": "string",
  "status": "string",
  "conflict_severity": "Conflict Severity",
  "classification_reason": "Classification Reason",
  "tech_version": "Tech Version",
  "server_version": "Server Version",
  "field_diffs": "Field Diffs"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/mobile-sync/state/test/{user_id}`
**Summary**: [TEST] Get sync state for a user — no auth required  

**Parameters**:
- `user_id` (path, string, required)
- `cursor` (query, , optional)
- `limit` (query, integer, optional, default: 50)
- `status` (query, , optional)

**Response 200**: `MobileSyncStateResponse`
```json
{
  "user_id": "string",
  "items": [
    {
      "id": "...",
      "device_id": "...",
      "operation_type": "...",
      "operation_payload_summary": "...",
      "status": "...",
      "conflict_severity": "...",
      "client_capture_at": "...",
      "synced_at": "..."
    }
  ],
  "cursor": "Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/mobile-sync/state/{user_id}`
**Summary**: Get sync state for a tech (owner/admin only)  
**Auth**: Required  

**Parameters**:
- `user_id` (path, string, required)
- `cursor` (query, , optional)
- `limit` (query, integer, optional, default: 50)
- `status` (query, , optional)

**Response 200**: `MobileSyncStateResponse`
```json
{
  "user_id": "string",
  "items": [
    {
      "id": "...",
      "device_id": "...",
      "operation_type": "...",
      "operation_payload_summary": "...",
      "status": "...",
      "conflict_severity": "...",
      "client_capture_at": "...",
      "synced_at": "..."
    }
  ],
  "cursor": "Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### nec

#### `GET /api/v1/nec/calc-logs`
**Summary**: List Nec Calc Logs  
**Auth**: Required  

**Parameters**:
- `job_id` (query, , optional)
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `Response List Nec Calc Logs Api V1 Nec Calc Logs Get`
```json
[
  {
    "id": "string",
    "calc_type": "string",
    "nec_guide_version": "string",
    "inputs_json": {},
    "result_json": {},
    "is_offline_calc": false,
    "client_capture_at": "Client Capture At",
    "job_id": "Job Id"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/nec/calc-logs`
**Summary**: Create Nec Calc Log  
**Auth**: Required  

**Request body**: `NecCalcLogCreate`
```json
{
  "calc_type": "string",
  "inputs": {},
  "result": {},
  "nec_guide_version": "string",
  "is_offline_calc": false,
  "client_capture_at": "Client Capture At",
  "idempotency_key": "Idempotency Key",
  "job_id": "Job Id"
}
```

**Response 201**: `Response Create Nec Calc Log Api V1 Nec Calc Logs Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/nec/calc-logs/test`
**Summary**: List Nec Calc Logs Test  

**Parameters**:
- `job_id` (query, , optional)
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `Response List Nec Calc Logs Test Api V1 Nec Calc Logs Test Get`
```json
[
  {
    "id": "string",
    "calc_type": "string",
    "nec_guide_version": "string",
    "inputs_json": {},
    "result_json": {},
    "is_offline_calc": false,
    "client_capture_at": "Client Capture At",
    "job_id": "Job Id"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/nec/calc-logs/test`
**Summary**: Create Nec Calc Log Test  

**Request body**: `NecCalcLogCreate`
```json
{
  "calc_type": "string",
  "inputs": {},
  "result": {},
  "nec_guide_version": "string",
  "is_offline_calc": false,
  "client_capture_at": "Client Capture At",
  "idempotency_key": "Idempotency Key",
  "job_id": "Job Id"
}
```

**Response 201**: `Response Create Nec Calc Log Test Api V1 Nec Calc Logs Test Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/nec/calculate`
**Summary**: Nec Calculate  
**Auth**: Required  

**Request body**: `NecCalculateRequest`
```json
{
  "calc_type": "string",
  "inputs": {},
  "job_id": "Job Id",
  "idempotency_key": "Idempotency Key"
}
```

**Response 201**: `NecCalculateResponse`
```json
{
  "log_id": "string",
  "calc_type": "string",
  "result": {},
  "nec_guide_version": "string",
  "nec_citation": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/nec/calculate/test`
**Summary**: Nec Calculate Test  

**Request body**: `NecCalculateRequest`
```json
{
  "calc_type": "string",
  "inputs": {},
  "job_id": "Job Id",
  "idempotency_key": "Idempotency Key"
}
```

**Response 201**: `NecCalculateResponse`
```json
{
  "log_id": "string",
  "calc_type": "string",
  "result": {},
  "nec_guide_version": "string",
  "nec_citation": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### notifications

#### `GET /api/v1/notifications/categories`
**Summary**: List Categories  
**Auth**: Required  

**Response 200**: `Response List Categories Api V1 Notifications Categories Get`

---

#### `POST /api/v1/notifications/in-app/mark-read`
**Summary**: Mark Read  
**Auth**: Required  

**Request body**: `MarkReadRequest`
```json
{
  "notification_ids": [
    "string"
  ]
}
```

**Response 200**: `Response Mark Read Api V1 Notifications In App Mark Read Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/in-app/recent`
**Summary**: Get Recent  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 50)

**Response 200**: `Response Get Recent Api V1 Notifications In App Recent Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/preferences`
**Summary**: Get Preferences  
**Auth**: Required  

**Parameters**:
- `user_id` (query, , optional)

**Response 200**: `Response Get Preferences Api V1 Notifications Preferences Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/notifications/preferences/mute-all-email`
**Summary**: Mute All Email  
**Auth**: Required  

**Response 200**: `Response Mute All Email Api V1 Notifications Preferences Mute All Email Post`

---

#### `POST /api/v1/notifications/preferences/mute-all-push-non-critical`
**Summary**: Mute All Push Non Critical  
**Auth**: Required  

**Response 200**: `Response Mute All Push Non Critical Api V1 Notifications Preferences Mute All Push Non Critical Post`

---

#### `POST /api/v1/notifications/preferences/reset-to-tenant-defaults`
**Summary**: Reset To Tenant Defaults  
**Auth**: Required  

**Response 200**: `Response Reset To Tenant Defaults Api V1 Notifications Preferences Reset To Tenant Defaults Post`

---

#### `PUT /api/v1/notifications/preferences/{category_id}/{channel}`
**Summary**: Set Preference  
**Auth**: Required  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Request body**: `PreferenceUpdate`
```json
{
  "enabled": false
}
```

**Response 200**: `NotificationPreferenceResponse`
```json
{
  "category_id": "string",
  "channel": "string",
  "enabled": false,
  "scope": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/notifications/preferences/{category_id}/{channel}`
**Summary**: Clear Preference  
**Auth**: Required  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Response 200**: `NotificationPreferenceClearResponse`
```json
{
  "cleared": false,
  "reverted_to_scope": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/sse/notifications`
**Summary**: SSE stream for in-app notifications (user-scoped)  
**Auth**: Required  

**Parameters**:
- `token` (query, , optional) — JWT token for SSE clients that cannot set headers

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/sub-triggers`
**Summary**: List Sub Triggers  
**Auth**: Required  

**Parameters**:
- `category_id` (query, , optional) — Filter by category_id

**Response 200**: `Response List Sub Triggers Api V1 Notifications Sub Triggers Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/tenant-policy`
**Summary**: Get Tenant Policy  
**Auth**: Required  

**Response 200**: `TenantPolicyListResponse`
```json
{
  "policies": [
    {
      "category_id": "...",
      "channel": "...",
      "enabled": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/notifications/tenant-policy`
**Summary**: Reset Tenant Policy  
**Auth**: Required  

**Response 200**: `TenantPolicyResetResponse`
```json
{
  "deleted_count": 0
}
```

---

#### `PUT /api/v1/notifications/tenant-policy/{category_id}/{channel}`
**Summary**: Set Tenant Policy  
**Auth**: Required  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Request body**: `PreferenceUpdate`
```json
{
  "enabled": false
}
```

**Response 200**: `Response Set Tenant Policy Api V1 Notifications Tenant Policy  Category Id   Channel  Put`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}`
**Summary**: Clear Tenant Policy  
**Auth**: Required  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Response 200**: `Response Clear Tenant Policy Api V1 Notifications Tenant Policy  Category Id   Channel  Delete`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/test/categories`
**Summary**: List Categories Test  

**Response 200**: `Response List Categories Test Api V1 Notifications Test Categories Get`

---

#### `POST /api/v1/notifications/test/in-app/mark-read`
**Summary**: Mark Read Test  

**Request body**: `MarkReadRequest`
```json
{
  "notification_ids": [
    "string"
  ]
}
```

**Response 200**: `Response Mark Read Test Api V1 Notifications Test In App Mark Read Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/test/in-app/recent`
**Summary**: Get Recent Test  

**Parameters**:
- `limit` (query, integer, optional, default: 50)

**Response 200**: `Response Get Recent Test Api V1 Notifications Test In App Recent Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/test/preferences`
**Summary**: Get Preferences Test  

**Parameters**:
- `user_id` (query, , optional)

**Response 200**: `Response Get Preferences Test Api V1 Notifications Test Preferences Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/notifications/test/preferences/mute-all-email`
**Summary**: Mute All Email Test  

**Response 200**: `Response Mute All Email Test Api V1 Notifications Test Preferences Mute All Email Post`

---

#### `POST /api/v1/notifications/test/preferences/mute-all-push-non-critical`
**Summary**: Mute All Push Non Critical Test  

**Response 200**: `Response Mute All Push Non Critical Test Api V1 Notifications Test Preferences Mute All Push Non Critical Post`

---

#### `POST /api/v1/notifications/test/preferences/reset-to-tenant-defaults`
**Summary**: Reset To Defaults Test  

**Response 200**: `Response Reset To Defaults Test Api V1 Notifications Test Preferences Reset To Tenant Defaults Post`

---

#### `PUT /api/v1/notifications/test/preferences/{category_id}/{channel}`
**Summary**: Set Preference Test  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Request body**: `PreferenceUpdate`
```json
{
  "enabled": false
}
```

**Response 200**: `NotificationPreferenceResponse`
```json
{
  "category_id": "string",
  "channel": "string",
  "enabled": false,
  "scope": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/notifications/test/preferences/{category_id}/{channel}`
**Summary**: Clear Preference Test  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Response 200**: `NotificationPreferenceClearResponse`
```json
{
  "cleared": false,
  "reverted_to_scope": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/test/sub-triggers`
**Summary**: List Sub Triggers Test  

**Parameters**:
- `category_id` (query, , optional)

**Response 200**: `Response List Sub Triggers Test Api V1 Notifications Test Sub Triggers Get`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/notifications/test/tenant-policy`
**Summary**: Get Tenant Policy Test  

**Response 200**: `TenantPolicyListResponse`
```json
{
  "policies": [
    {
      "category_id": "...",
      "channel": "...",
      "enabled": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/notifications/test/tenant-policy`
**Summary**: Reset Tenant Policy Test  

**Response 200**: `TenantPolicyResetResponse`
```json
{
  "deleted_count": 0
}
```

---

#### `PUT /api/v1/notifications/test/tenant-policy/{category_id}/{channel}`
**Summary**: Set Tenant Policy Test  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Request body**: `PreferenceUpdate`
```json
{
  "enabled": false
}
```

**Response 200**: `Response Set Tenant Policy Test Api V1 Notifications Test Tenant Policy  Category Id   Channel  Put`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/notifications/test/tenant-policy/{category_id}/{channel}`
**Summary**: Clear Tenant Policy Test  

**Parameters**:
- `category_id` (path, string, required)
- `channel` (path, string, required)

**Response 200**: `Response Clear Tenant Policy Test Api V1 Notifications Test Tenant Policy  Category Id   Channel  Delete`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### onboarding

#### `GET /api/v1/tenants/{tenant_id}/onboarding/checklist`
**Summary**: Get Onboarding Checklist  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `OnboardingChecklistResponse`
```json
{
  "tenant_id": "string",
  "account_created": false,
  "legal_accepted": false,
  "tier_selected": false,
  "first_customer_added": false,
  "first_customer_added_at": "First Customer Added At",
  "catalog_setup": false,
  "catalog_setup_at": "Catalog Setup At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed`
**Summary**: Dismiss Checklist Route  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed/test`
**Summary**: Dismiss Checklist Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden`
**Summary**: Hide Checklist Route  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `HideChecklistRequest`
```json
{
  "hidden": false
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden/test`
**Summary**: Hide Checklist Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `HideChecklistRequest`
```json
{
  "hidden": false
}
```

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}`
**Summary**: Skip Checklist Item  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)
- `item` (path, string, required)

**Response 200**: `OnboardingChecklistResponse`
```json
{
  "tenant_id": "string",
  "account_created": false,
  "legal_accepted": false,
  "tier_selected": false,
  "first_customer_added": false,
  "first_customer_added_at": "First Customer Added At",
  "catalog_setup": false,
  "catalog_setup_at": "Catalog Setup At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}/test`
**Summary**: Skip Checklist Item Test  

**Parameters**:
- `tenant_id` (path, string, required)
- `item` (path, string, required)

**Response 200**: `OnboardingChecklistResponse`
```json
{
  "tenant_id": "string",
  "account_created": false,
  "legal_accepted": false,
  "tier_selected": false,
  "first_customer_added": false,
  "first_customer_added_at": "First Customer Added At",
  "catalog_setup": false,
  "catalog_setup_at": "Catalog Setup At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/onboarding/checklist/test`
**Summary**: Get Onboarding Checklist Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `OnboardingChecklistResponse`
```json
{
  "tenant_id": "string",
  "account_created": false,
  "legal_accepted": false,
  "tier_selected": false,
  "first_customer_added": false,
  "first_customer_added_at": "First Customer Added At",
  "catalog_setup": false,
  "catalog_setup_at": "Catalog Setup At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### operator

#### `GET /api/v1/operator/auth/me`
**Summary**: Get Auth Me  
**Auth**: Required  

**Response 200**: `AuthMeResponse`
```json
{
  "user_type": "string",
  "user_id": "string",
  "email": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "platform_role_code": "Platform Role Code",
  "tenant_id": "Tenant Id",
  "role_code": "Role Code"
}
```

---

#### `GET /api/v1/operator/cohort`
**Summary**: Get Cohort  
**Auth**: Required  

**Response 200**: `CohortOverviewResponse`
```json
{
  "cohort_tier_name": "string",
  "cohort_is_active": false,
  "signup_cap": 0,
  "members": [
    {
      "tenant_id": "...",
      "business_name": "...",
      "charter_member_number": "...",
      "free_period_ends_at": "...",
      "days_remaining": "...",
      "stripe_status": "...",
      "has_payment_method": "...",
      "messaging_status": "..."
    }
  ]
}
```

---

#### `POST /api/v1/operator/cohort/close`
**Summary**: Close Charter Cohort  
**Auth**: Required  

**Response 200**: `CloseCohortResponse`
```json
{
  "charter_price_archived": false,
  "charter_tier_deactivated": false,
  "activated_tiers": [
    "string"
  ]
}
```

---

#### `POST /api/v1/operator/cohort/{tenant_id}/extend`
**Summary**: Extend Member Free Period  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ExtendFreePeriodRequest`
```json
{
  "new_free_period_ends_at": "string",
  "override_reason": "string"
}
```

**Response 200**: `ExtendFreePeriodResponse`
```json
{
  "tenant_id": "string",
  "previous_free_period_ends_at": "Previous Free Period Ends At",
  "new_free_period_ends_at": "string",
  "stripe_subscription_id": "string",
  "stripe_trial_end_updated": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/operator/impersonation/end`
**Summary**: End Impersonation Endpoint  
**Auth**: Required  

**Request body**: `ImpersonationEndRequest`
```json
{
  "tenant_id": "string"
}
```

**Response 200**: `ImpersonationEndResponse`
```json
{
  "ended": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/operator/impersonation/start`
**Summary**: Start Impersonation Endpoint  
**Auth**: Required  

**Request body**: `ImpersonationStartRequest`
```json
{
  "tenant_id": "string"
}
```

**Response 200**: `ImpersonationSessionResponse`
```json
{
  "tenant_id": "string",
  "tenant_name": "string",
  "impersonator_user_id": "string",
  "role_code": "string",
  "started_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/operator/tenants`
**Summary**: List Tenants  
**Auth**: Required  

**Response 200**: `OperatorTenantListResponse`
```json
{
  "tenants": [
    {
      "tenant_id": "...",
      "name": "...",
      "is_active": "...",
      "tier_name": "...",
      "subscription_status": "...",
      "created_at": "..."
    }
  ]
}
```

---

### owner-escalations

#### `GET /api/v1/owner/field-issues/summary`
**Summary**: Pending field issues count for owner dashboard (BETA-B1)  
**Auth**: Required  

**Response 200**: `FieldIssuesSummaryResponse`
```json
{
  "pending_count": 0
}
```

---

#### `GET /api/v1/owner/field-issues/summary/test`
**Summary**: [TEST] Pending field issues count (no JWT)  

**Response 200**: `FieldIssuesSummaryResponse`
```json
{
  "pending_count": 0
}
```

---

#### `GET /api/v1/owner/mobile-sync-escalations`
**Summary**: List mobile sync owner escalations (A47)  
**Auth**: Required  

**Parameters**:
- `escalation_status` (query, string, optional, default: pending)
- `operation_type` (query, , optional)
- `sort` (query, string, optional, default: -escalated_at)
- `cursor` (query, , optional)
- `limit` (query, integer, optional, default: 25)

**Response 200**: `EscalationListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "originating_user_id": "...",
      "originating_user_name": "...",
      "operation_type": "...",
      "conflict_severity": "...",
      "escalation_reason": "...",
      "escalation_reason_explainer": "...",
      "status": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "total_pending": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/owner/mobile-sync-escalations/history`
**Summary**: Historical archive of resolved escalations (A47)  
**Auth**: Required  

**Parameters**:
- `resolved_at_after` (query, , optional)
- `resolved_at_before` (query, , optional)
- `operation_type` (query, , optional)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `EscalationHistoryResponse`
```json
{
  "items": [
    {
      "id": "...",
      "originating_user_id": "...",
      "operation_type": "...",
      "conflict_severity": "...",
      "escalation_reason": "...",
      "status": "...",
      "escalated_at": "...",
      "resolved_at": "..."
    }
  ],
  "total": 0,
  "offset": 0,
  "limit": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/owner/mobile-sync-escalations/history/test`
**Summary**: [TEST] List escalation history (no JWT)  

**Parameters**:
- `resolved_at_after` (query, , optional)
- `resolved_at_before` (query, , optional)
- `operation_type` (query, , optional)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `EscalationHistoryResponse`
```json
{
  "items": [
    {
      "id": "...",
      "originating_user_id": "...",
      "operation_type": "...",
      "conflict_severity": "...",
      "escalation_reason": "...",
      "status": "...",
      "escalated_at": "...",
      "resolved_at": "..."
    }
  ],
  "total": 0,
  "offset": 0,
  "limit": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/owner/mobile-sync-escalations/test`
**Summary**: [TEST] List escalations (no JWT)  

**Parameters**:
- `escalation_status` (query, string, optional, default: pending)
- `operation_type` (query, , optional)
- `sort` (query, string, optional, default: -escalated_at)
- `limit` (query, integer, optional, default: 25)

**Response 200**: `EscalationListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "originating_user_id": "...",
      "originating_user_name": "...",
      "operation_type": "...",
      "conflict_severity": "...",
      "escalation_reason": "...",
      "escalation_reason_explainer": "...",
      "status": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "total_pending": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/owner/mobile-sync-escalations/{escalation_id}`
**Summary**: Get escalation detail (A47)  
**Auth**: Required  

**Parameters**:
- `escalation_id` (path, string, required)

**Response 200**: `EscalationDetailResponse`
```json
{
  "id": "string",
  "originating_user_id": "string",
  "conflict_id": "string",
  "escalation_reason": "string",
  "escalation_reason_explainer": "string",
  "escalation_type": "Escalation Type",
  "status": "string",
  "escalated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/owner/mobile-sync-escalations/{escalation_id}/resolve`
**Summary**: Resolve an owner escalation (A48)  
**Auth**: Required  

**Parameters**:
- `escalation_id` (path, string, required)

**Request body**: `EscalationResolveRequest`
```json
{
  "resolution": "Resolution",
  "expected_server_state_at_view_time": "Expected Server State At View Time",
  "resolution_action": "Resolution Action",
  "resolution_payload": "Resolution Payload",
  "expected_escalation_updated_at": "Expected Escalation Updated At"
}
```

**Response 200**: `EscalationResolveResponse`
```json
{
  "committed": false,
  "resolution_outcome": "string",
  "post_commit_state": "Post Commit State",
  "originator_notification_dispatched": false,
  "id": "Id",
  "status": "Status",
  "resolution_action": "Resolution Action",
  "resolved_at": "Resolved At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/owner/mobile-sync-escalations/{escalation_id}/resolve/test`
**Summary**: [TEST] Resolve escalation (no JWT)  

**Parameters**:
- `escalation_id` (path, string, required)

**Request body**: `EscalationResolveRequest`
```json
{
  "resolution": "Resolution",
  "expected_server_state_at_view_time": "Expected Server State At View Time",
  "resolution_action": "Resolution Action",
  "resolution_payload": "Resolution Payload",
  "expected_escalation_updated_at": "Expected Escalation Updated At"
}
```

**Response 200**: `EscalationResolveResponse`
```json
{
  "committed": false,
  "resolution_outcome": "string",
  "post_commit_state": "Post Commit State",
  "originator_notification_dispatched": false,
  "id": "Id",
  "status": "Status",
  "resolution_action": "Resolution Action",
  "resolved_at": "Resolved At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/owner/mobile-sync-escalations/{escalation_id}/test`
**Summary**: [TEST] Get escalation detail (no JWT)  

**Parameters**:
- `escalation_id` (path, string, required)

**Response 200**: `EscalationDetailResponse`
```json
{
  "id": "string",
  "originating_user_id": "string",
  "conflict_id": "string",
  "escalation_reason": "string",
  "escalation_reason_explainer": "string",
  "escalation_type": "Escalation Type",
  "status": "string",
  "escalated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### payment-schedules

#### `GET /api/v1/payment-schedules`
**Summary**: List Schedules  
**Auth**: Required  

**Parameters**:
- `quote_id` (query, , optional)
- `job_id` (query, , optional)
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `PaymentScheduleListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "quote_id": "...",
      "job_id": "...",
      "customer_id": "...",
      "site_id": "...",
      "contract_total_cents": "...",
      "status": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules`
**Summary**: Create Schedule  
**Auth**: Required  

**Request body**: `PaymentScheduleCreate`
```json
{
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "basis_default": "string",
  "lines": [
    {
      "sequence": "...",
      "label": "...",
      "basis": "...",
      "percent": "...",
      "amount_cents": "...",
      "trigger_type": "...",
      "trigger_date": "...",
      "milestone_label": "..."
    }
  ],
  "idempotency_key": "Idempotency Key"
}
```

**Response 201**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/payment-schedules/test`
**Summary**: List Schedules Test  

**Parameters**:
- `quote_id` (query, , optional)
- `job_id` (query, , optional)
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `PaymentScheduleListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "quote_id": "...",
      "job_id": "...",
      "customer_id": "...",
      "site_id": "...",
      "contract_total_cents": "...",
      "status": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/test`
**Summary**: Create Schedule Test  

**Request body**: `PaymentScheduleCreate`
```json
{
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "basis_default": "string",
  "lines": [
    {
      "sequence": "...",
      "label": "...",
      "basis": "...",
      "percent": "...",
      "amount_cents": "...",
      "trigger_type": "...",
      "trigger_date": "...",
      "milestone_label": "..."
    }
  ],
  "idempotency_key": "Idempotency Key"
}
```

**Response 201**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/payment-schedules/{schedule_id}`
**Summary**: Get Schedule  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)

**Response 200**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/payment-schedules/{schedule_id}`
**Summary**: Update Schedule  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)

**Request body**: `PaymentScheduleUpdate`
```json
{
  "contract_total_cents": "Contract Total Cents",
  "basis_default": "Basis Default"
}
```

**Response 200**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/{schedule_id}/activate`
**Summary**: Activate Schedule Route  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)

**Request body**: `PaymentScheduleActivateRequest`
```json
{}
```

**Response 200**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/{schedule_id}/activate/test`
**Summary**: Activate Schedule Test  

**Parameters**:
- `schedule_id` (path, string, required)

**Request body**: `PaymentScheduleActivateRequest`
```json
{}
```

**Response 200**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/{schedule_id}/lines`
**Summary**: Add Line  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)

**Request body**: `PaymentScheduleLineCreate`
```json
{
  "sequence": 0,
  "label": "string",
  "basis": "string",
  "percent": "Percent",
  "amount_cents": "Amount Cents",
  "trigger_type": "string",
  "trigger_date": "Trigger Date",
  "milestone_label": "Milestone Label"
}
```

**Response 201**: `PaymentScheduleLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "payment_schedule_id": "string",
  "sequence": 0,
  "label": "string",
  "basis": "string",
  "percent": "Percent",
  "amount_cents": "Amount Cents"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/{schedule_id}/lines/test`
**Summary**: Add Line Test  

**Parameters**:
- `schedule_id` (path, string, required)

**Request body**: `PaymentScheduleLineCreate`
```json
{
  "sequence": 0,
  "label": "string",
  "basis": "string",
  "percent": "Percent",
  "amount_cents": "Amount Cents",
  "trigger_type": "string",
  "trigger_date": "Trigger Date",
  "milestone_label": "Milestone Label"
}
```

**Response 201**: `PaymentScheduleLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "payment_schedule_id": "string",
  "sequence": 0,
  "label": "string",
  "basis": "string",
  "percent": "Percent",
  "amount_cents": "Amount Cents"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/payment-schedules/{schedule_id}/lines/{line_id}`
**Summary**: Update Line  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)
- `line_id` (path, string, required)

**Request body**: `PaymentScheduleLineUpdate`
```json
{
  "sequence": "Sequence",
  "label": "Label",
  "basis": "Basis",
  "percent": "Percent",
  "amount_cents": "Amount Cents",
  "trigger_type": "Trigger Type",
  "trigger_date": "Trigger Date",
  "milestone_label": "Milestone Label"
}
```

**Response 200**: `PaymentScheduleLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "payment_schedule_id": "string",
  "sequence": 0,
  "label": "string",
  "basis": "string",
  "percent": "Percent",
  "amount_cents": "Amount Cents"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/payment-schedules/{schedule_id}/lines/{line_id}`
**Summary**: Delete Line  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)
- `line_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/{schedule_id}/lines/{line_id}/generate-invoice`
**Summary**: Generate Invoice  
**Auth**: Required  

**Parameters**:
- `schedule_id` (path, string, required)
- `line_id` (path, string, required)

**Request body**: `DrawInvoiceGenerateRequest`
```json
{
  "idempotency_key": "Idempotency Key"
}
```

**Response 201**: `InvoiceResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_number": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "string",
  "quote_id": "Quote Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/payment-schedules/{schedule_id}/lines/{line_id}/generate-invoice/test`
**Summary**: Generate Invoice Test  

**Parameters**:
- `schedule_id` (path, string, required)
- `line_id` (path, string, required)

**Request body**: `DrawInvoiceGenerateRequest`
```json
{
  "idempotency_key": "Idempotency Key"
}
```

**Response 201**: `InvoiceResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "invoice_number": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "string",
  "quote_id": "Quote Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/payment-schedules/{schedule_id}/lines/{line_id}/test`
**Summary**: Update Line Test  

**Parameters**:
- `schedule_id` (path, string, required)
- `line_id` (path, string, required)

**Request body**: `PaymentScheduleLineUpdate`
```json
{
  "sequence": "Sequence",
  "label": "Label",
  "basis": "Basis",
  "percent": "Percent",
  "amount_cents": "Amount Cents",
  "trigger_type": "Trigger Type",
  "trigger_date": "Trigger Date",
  "milestone_label": "Milestone Label"
}
```

**Response 200**: `PaymentScheduleLineResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "payment_schedule_id": "string",
  "sequence": 0,
  "label": "string",
  "basis": "string",
  "percent": "Percent",
  "amount_cents": "Amount Cents"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/payment-schedules/{schedule_id}/lines/{line_id}/test`
**Summary**: Delete Line Test  

**Parameters**:
- `schedule_id` (path, string, required)
- `line_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/payment-schedules/{schedule_id}/test`
**Summary**: Get Schedule Test  

**Parameters**:
- `schedule_id` (path, string, required)

**Response 200**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/payment-schedules/{schedule_id}/test`
**Summary**: Update Schedule Test  

**Parameters**:
- `schedule_id` (path, string, required)

**Request body**: `PaymentScheduleUpdate`
```json
{
  "contract_total_cents": "Contract Total Cents",
  "basis_default": "Basis Default"
}
```

**Response 200**: `PaymentScheduleResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "quote_id": "Quote Id",
  "job_id": "Job Id",
  "customer_id": "string",
  "site_id": "string",
  "contract_total_cents": 0,
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### photos

#### `POST /api/v1/photos/complete-upload`
**Summary**: Complete S3 multipart photo upload  
**Auth**: Required  

**Request body**: `CompleteUploadRequest`
```json
{
  "pilot_photo_id": "string",
  "s3_upload_session_id": "string",
  "chunk_etags": [
    {
      "part_number": "...",
      "etag": "..."
    }
  ]
}
```

**Response 200**: `CompleteUploadResponse`
```json
{
  "id": "string",
  "job_id": "string",
  "file_name": "string",
  "mime_type": "string",
  "size_bytes": 0,
  "object_key": "string",
  "upload_completed_at": "Upload Completed At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/photos/complete-upload/test`
**Summary**: [TEST] Complete photo upload (no JWT)  

**Request body**: `CompleteUploadRequest`
```json
{
  "pilot_photo_id": "string",
  "s3_upload_session_id": "string",
  "chunk_etags": [
    {
      "part_number": "...",
      "etag": "..."
    }
  ]
}
```

**Response 200**: `CompleteUploadResponse`
```json
{
  "id": "string",
  "job_id": "string",
  "file_name": "string",
  "mime_type": "string",
  "size_bytes": 0,
  "object_key": "string",
  "upload_completed_at": "Upload Completed At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/photos/initiate-upload`
**Summary**: Initiate S3 multipart photo upload  
**Auth**: Required  

**Request body**: `InitiateUploadRequest`
```json
{
  "job_id": "string",
  "expense_id": "Expense Id",
  "file_size_bytes": 0,
  "mime_type": "string",
  "file_name": "string",
  "client_capture_at": "Client Capture At",
  "idempotency_uuid": "string"
}
```

**Response 201**: `InitiateUploadResponse`
```json
{
  "pilot_photo_id": "string",
  "s3_upload_session_id": "string",
  "presigned_chunk_urls": [
    "string"
  ],
  "chunk_size_bytes": 0,
  "chunk_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/photos/initiate-upload/test`
**Summary**: [TEST] Initiate photo upload (no JWT)  

**Request body**: `InitiateUploadRequest`
```json
{
  "job_id": "string",
  "expense_id": "Expense Id",
  "file_size_bytes": 0,
  "mime_type": "string",
  "file_name": "string",
  "client_capture_at": "Client Capture At",
  "idempotency_uuid": "string"
}
```

**Response 201**: `InitiateUploadResponse`
```json
{
  "pilot_photo_id": "string",
  "s3_upload_session_id": "string",
  "presigned_chunk_urls": [
    "string"
  ],
  "chunk_size_bytes": 0,
  "chunk_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### public

#### `GET /api/v1/public/charter-availability`
**Summary**: Get Charter Availability  

**Response 200**: `CharterAvailabilityResponse`
```json
{
  "open": false,
  "remaining": 0
}
```

---

#### `GET /api/v1/public/invoices/{signed_token}`
**Summary**: Get Public Invoice  

**Parameters**:
- `signed_token` (path, string, required)

**Response 200**: `PublicInvoiceResponse`
```json
{
  "invoice_id": "string",
  "tenant_name": "string",
  "customer_name": "string",
  "invoice_total_cents": 0,
  "amount_paid_cents": 0,
  "amount_due_cents": 0,
  "currency": "string",
  "line_items": [
    {}
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/public/invoices/{signed_token}/confirm-payment`
**Summary**: Confirm Payment  

**Parameters**:
- `signed_token` (path, string, required)

**Request body**: `ConfirmPaymentRequest`
```json
{
  "payment_intent_id": "string"
}
```

**Response 200**: `ConfirmPaymentResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/public/invoices/{signed_token}/payment-intent`
**Summary**: Create Payment Intent  

**Parameters**:
- `signed_token` (path, string, required)

**Request body**: `PaymentIntentRequest`
```json
{
  "amount_cents": 0,
  "comment": "Comment"
}
```

**Response 200**: `PaymentIntentResponse`
```json
{
  "client_secret": "string",
  "payment_intent_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/public/quotes/{signed_token}`
**Summary**: Get Public Quote  

**Parameters**:
- `signed_token` (path, string, required)

**Response 200**: `PublicQuoteResponse`
```json
{
  "quote_id": "string",
  "tenant_name": "string",
  "customer_name": "string",
  "quote_total_cents": 0,
  "currency": "string",
  "line_items": [
    {}
  ],
  "status": "string",
  "expires_at": "Expires At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/public/quotes/{signed_token}/accept`
**Summary**: Accept Public Quote  

**Parameters**:
- `signed_token` (path, string, required)

**Request body**: `AcceptQuoteRequest`
```json
{
  "comment": "Comment"
}
```

**Response 200**: `AcceptQuoteResponse`
```json
{
  "status": "string",
  "accepted_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/public/quotes/{signed_token}/decline`
**Summary**: Decline Public Quote  

**Parameters**:
- `signed_token` (path, string, required)

**Request body**: `DeclineQuoteRequest`
```json
{
  "reason": "string",
  "comment": "Comment"
}
```

**Response 200**: `DeclineQuoteResponse`
```json
{
  "status": "string",
  "declined_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/public/tenant-sites/{slug}`
**Summary**: Get published tenant site (public, no auth)  

**Parameters**:
- `slug` (path, string, required)

**Response 200**: `PublicTenantSiteResponse`
```json
{
  "slug": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email",
  "public_phone": "Public Phone",
  "public_city": "Public City",
  "public_state": "Public State",
  "public_address_line1": "Public Address Line1"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/short/{short_code}`
**Summary**: Redirect Short Code  

**Parameters**:
- `short_code` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### quote-templates

#### `GET /api/v1/quote-templates`
**Summary**: List quote templates  
**Auth**: Required  

**Parameters**:
- `style` (query, , optional)
- `category` (query, , optional)
- `system_only` (query, boolean, optional, default: False)
- `tenant_only` (query, boolean, optional, default: False)

**Response 200**: `Response List Quote Templates Api V1 Quote Templates Get`
```json
[
  {
    "id": "string",
    "tenant_id": "Tenant Id",
    "name": "string",
    "style": "string",
    "category": "Category",
    "description": "Description",
    "is_system_template": false,
    "current_version": 0
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates`
**Summary**: Create a tenant quote template  
**Auth**: Required  

**Request body**: `QuoteTemplateCreate`
```json
{
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "lines": [
    {
      "qco_line_type_id": "...",
      "description": "...",
      "default_quantity": "...",
      "default_unit_price_cents": "...",
      "customer_visible": "...",
      "is_section_header": "...",
      "display_order": "...",
      "parent_line_id": "..."
    }
  ]
}
```

**Response 201**: `QuoteTemplateResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "is_system_template": false,
  "current_version": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/from-template/{template_id}`
**Summary**: Instantiate a new quote from a template  
**Auth**: Required  

**Parameters**:
- `template_id` (path, string, required)

**Request body**: `QuoteFromTemplateRequest`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "variable_overrides": {}
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/from-template/{template_id}/test`
**Summary**: Create a quote from a template (TEST — no auth)  

**Parameters**:
- `template_id` (path, string, required)

**Request body**: `QuoteFromTemplateRequest`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "variable_overrides": {}
}
```

**Response 201**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quote-templates/test`
**Summary**: List quote templates (TEST — no auth)  

**Parameters**:
- `style` (query, , optional)
- `category` (query, , optional)
- `system_only` (query, boolean, optional, default: False)
- `tenant_only` (query, boolean, optional, default: False)

**Response 200**: `Response List Quote Templates Test Api V1 Quote Templates Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "Tenant Id",
    "name": "string",
    "style": "string",
    "category": "Category",
    "description": "Description",
    "is_system_template": false,
    "current_version": 0
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/test`
**Summary**: Create a tenant quote template (TEST — no auth)  

**Request body**: `QuoteTemplateCreate`
```json
{
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "lines": [
    {
      "qco_line_type_id": "...",
      "description": "...",
      "default_quantity": "...",
      "default_unit_price_cents": "...",
      "customer_visible": "...",
      "is_section_header": "...",
      "display_order": "...",
      "parent_line_id": "..."
    }
  ]
}
```

**Response 201**: `QuoteTemplateResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "is_system_template": false,
  "current_version": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/{id}/disable`
**Summary**: Soft-disable a quote template  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `QuoteTemplateResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "is_system_template": false,
  "current_version": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/{id}/disable/test`
**Summary**: Soft-disable a quote template (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `QuoteTemplateResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "is_system_template": false,
  "current_version": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/{id}/fork`
**Summary**: Fork a system template into a tenant copy  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteTemplateForkRequest`
```json
{
  "name": "Name"
}
```

**Response 201**: `QuoteTemplateResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "is_system_template": false,
  "current_version": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quote-templates/{id}/fork/test`
**Summary**: Fork a system template (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteTemplateForkRequest`
```json
{
  "name": "Name"
}
```

**Response 201**: `QuoteTemplateResponse`
```json
{
  "id": "string",
  "tenant_id": "Tenant Id",
  "name": "string",
  "style": "string",
  "category": "Category",
  "description": "Description",
  "is_system_template": false,
  "current_version": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### quotes

#### `GET /api/v1/qco-line-types`
**Summary**: List Qco Line Types  
**Auth**: Required  

**Response 200**: `Response List Qco Line Types Api V1 Qco Line Types Get`
```json
[
  {
    "id": "string",
    "code": "string",
    "name": "string",
    "is_default": false,
    "is_active": false,
    "is_tenant_override": false
  }
]
```

---

#### `GET /api/v1/qco-line-types/test`
**Summary**: List Qco Line Types Test  

**Response 200**: `Response List Qco Line Types Test Api V1 Qco Line Types Test Get`
```json
[
  {
    "id": "string",
    "code": "string",
    "name": "string",
    "is_default": false,
    "is_active": false,
    "is_tenant_override": false
  }
]
```

---

#### `GET /api/v1/quotes`
**Summary**: List Quotes  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `status` (query, , optional)
- `customer_search` (query, , optional)
- `title_search` (query, , optional)
- `date_from` (query, , optional)
- `date_to` (query, , optional)
- `customer_id` (query, , optional) — Filter quotes by exact customer UUID

**Response 200**: `PaginatedQuoteListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "site_id": "...",
      "status_id": "...",
      "status_code": "...",
      "subtotal_cents": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes`
**Summary**: Create Quote  
**Auth**: Required  

**Request body**: `QuoteCreate`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "currency": "string",
  "idempotency_key": "Idempotency Key",
  "expires_at": "Expires At",
  "title": "Title",
  "card_required": "Card Required"
}
```

**Response 201**: `QuoteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "Status Code",
  "subtotal_cents": 0,
  "tax_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/public/{token}/accept`
**Summary**: Accept Quote Via Public Link  

**Parameters**:
- `token` (path, string, required)

**Request body**: `QuoteAcceptanceCreate`
```json
{
  "accepted_by_name": "string",
  "accepted_by_email": "string",
  "signature_url": "string",
  "acceptance_notes": "Acceptance Notes",
  "ip_address": "Ip Address",
  "user_agent": "User Agent"
}
```

**Response 200**: `QuoteAcceptanceResponse`
```json
{
  "id": "string",
  "quote_version_id": "string",
  "contact_id": "Contact Id",
  "accepted_by_name": "string",
  "accepted_by_email": "string",
  "accepted_by_user_id": "Accepted By User Id",
  "approved_at": "string",
  "approved_ip": "Approved Ip"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/quotes/{quote_id}/accept`
**Summary**: Accept Quote  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteAcceptanceCreate`
```json
{
  "accepted_by_name": "string",
  "accepted_by_email": "string",
  "signature_url": "string",
  "acceptance_notes": "Acceptance Notes",
  "ip_address": "Ip Address",
  "user_agent": "User Agent"
}
```

**Response 200**: `QuoteAcceptanceResponse`
```json
{
  "id": "string",
  "quote_version_id": "string",
  "contact_id": "Contact Id",
  "accepted_by_name": "string",
  "accepted_by_email": "string",
  "accepted_by_user_id": "Accepted By User Id",
  "approved_at": "string",
  "approved_ip": "Approved Ip"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/test`
**Summary**: List Quotes Test  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 25)
- `offset` (query, integer, optional, default: 0)
- `status` (query, , optional)
- `customer_search` (query, , optional)
- `title_search` (query, , optional)
- `date_from` (query, , optional)
- `date_to` (query, , optional)
- `customer_id` (query, , optional) — Filter quotes by exact customer UUID

**Response 200**: `PaginatedQuoteListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "customer_name": "...",
      "site_id": "...",
      "status_id": "...",
      "status_code": "...",
      "subtotal_cents": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/test`
**Summary**: Create Quote Test  

**Request body**: `QuoteCreate`
```json
{
  "customer_id": "string",
  "site_id": "string",
  "currency": "string",
  "idempotency_key": "Idempotency Key",
  "expires_at": "Expires At",
  "title": "Title",
  "card_required": "Card Required"
}
```

**Response 201**: `QuoteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "Status Code",
  "subtotal_cents": 0,
  "tax_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/test/quotes/{quote_id}/accept`
**Summary**: Accept Quote Test  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteAcceptanceCreate`
```json
{
  "accepted_by_name": "string",
  "accepted_by_email": "string",
  "signature_url": "string",
  "acceptance_notes": "Acceptance Notes",
  "ip_address": "Ip Address",
  "user_agent": "User Agent"
}
```

**Response 200**: `QuoteAcceptanceResponse`
```json
{
  "id": "string",
  "quote_version_id": "string",
  "contact_id": "Contact Id",
  "accepted_by_name": "string",
  "accepted_by_email": "string",
  "accepted_by_user_id": "Accepted By User Id",
  "approved_at": "string",
  "approved_ip": "Approved Ip"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{id}/analytics`
**Summary**: Get quote view analytics timeline  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `QuoteAnalyticsResponse`
```json
{
  "events": [
    {
      "action_name": "...",
      "contact_name": "...",
      "occurred_at": "...",
      "ip_address": "...",
      "user_agent": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{id}/analytics/test`
**Summary**: [TEST] Get quote view analytics timeline (no auth)  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `QuoteAnalyticsResponse`
```json
{
  "events": [
    {
      "action_name": "...",
      "contact_name": "...",
      "occurred_at": "...",
      "ip_address": "...",
      "user_agent": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/apply-discount`
**Summary**: Apply a time-limited discount to a quote  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteApplyDiscountRequest`
```json
{
  "discount_pct": "Discount Pct",
  "discount_expires_at": "Discount Expires At",
  "expected_quote_version_id": "Expected Quote Version Id"
}
```

**Response 201**: `QuoteApplyDiscountResponse`
```json
{
  "quote_id": "string",
  "discount_pct": "string",
  "discount_amount_cents": 0,
  "discount_expires_at": "Discount Expires At",
  "new_version_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/apply-discount/test`
**Summary**: Apply a discount to a quote (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteApplyDiscountRequest`
```json
{
  "discount_pct": "Discount Pct",
  "discount_expires_at": "Discount Expires At",
  "expected_quote_version_id": "Expected Quote Version Id"
}
```

**Response 201**: `QuoteApplyDiscountResponse`
```json
{
  "quote_id": "string",
  "discount_pct": "string",
  "discount_amount_cents": 0,
  "discount_expires_at": "Discount Expires At",
  "new_version_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/approve`
**Summary**: Approve a pending quote  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteApproveRequest`
```json
{
  "expected_quote_version_id": "Expected Quote Version Id"
}
```

**Response 200**: `QuoteApproveResponse`
```json
{
  "quote_id": "string",
  "status": "string",
  "approved_at": "string",
  "approved_by_user_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/approve/test`
**Summary**: Approve a pending quote (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteApproveRequest`
```json
{
  "expected_quote_version_id": "Expected Quote Version Id"
}
```

**Response 200**: `QuoteApproveResponse`
```json
{
  "quote_id": "string",
  "status": "string",
  "approved_at": "string",
  "approved_by_user_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{id}/comments`
**Summary**: Get all approval comments for a quote  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `Response Get Quote Comments Api V1 Quotes  Id  Comments Get`
```json
[
  {
    "id": "string",
    "quote_id": "string",
    "quote_version_id": "string",
    "target_line_id": "Target Line Id",
    "author_user_id": "string",
    "comment_type": "string",
    "content": "string",
    "created_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{id}/comments/test`
**Summary**: Get quote approval comments (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `Response Get Quote Comments Test Api V1 Quotes  Id  Comments Test Get`
```json
[
  {
    "id": "string",
    "quote_id": "string",
    "quote_version_id": "string",
    "target_line_id": "Target Line Id",
    "author_user_id": "string",
    "comment_type": "string",
    "content": "string",
    "created_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/kickback`
**Summary**: Kick back a pending_approval quote to draft  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteKickbackRequest`
```json
{
  "expected_quote_version_id": "Expected Quote Version Id",
  "overall_comment": "Overall Comment",
  "line_comments": "Line Comments"
}
```

**Response 200**: `QuoteKickbackResponse`
```json
{
  "quote_id": "string",
  "status": "string",
  "comment_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/kickback/test`
**Summary**: Kick back a quote to draft (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteKickbackRequest`
```json
{
  "expected_quote_version_id": "Expected Quote Version Id",
  "overall_comment": "Overall Comment",
  "line_comments": "Line Comments"
}
```

**Response 200**: `QuoteKickbackResponse`
```json
{
  "quote_id": "string",
  "status": "string",
  "comment_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{id}/pending-edits`
**Summary**: List pending edits for a quote  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `Response List Pending Edits Api V1 Quotes  Id  Pending Edits Get`
```json
[
  {
    "id": "string",
    "quote_id": "string",
    "quote_version_id": "string",
    "editor_user_id": "string",
    "edit_type": "string",
    "target_line_id": "Target Line Id",
    "edit_payload": {},
    "annotation": "Annotation"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/pending-edits`
**Summary**: Create a pending edit  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuotePendingEditCreate`
```json
{
  "edit_type": "string",
  "target_line_id": "Target Line Id",
  "edit_payload": {},
  "annotation": "Annotation"
}
```

**Response 201**: `QuotePendingEditResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "quote_version_id": "string",
  "editor_user_id": "string",
  "edit_type": "string",
  "target_line_id": "Target Line Id",
  "edit_payload": {},
  "annotation": "Annotation"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/quotes/{id}/pending-edits`
**Summary**: Delete all pending edits for current user on this quote  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{id}/pending-edits/test`
**Summary**: List pending edits for a quote (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `Response List Pending Edits Test Api V1 Quotes  Id  Pending Edits Test Get`
```json
[
  {
    "id": "string",
    "quote_id": "string",
    "quote_version_id": "string",
    "editor_user_id": "string",
    "edit_type": "string",
    "target_line_id": "Target Line Id",
    "edit_payload": {},
    "annotation": "Annotation"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/pending-edits/test`
**Summary**: Create a pending edit (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuotePendingEditCreate`
```json
{
  "edit_type": "string",
  "target_line_id": "Target Line Id",
  "edit_payload": {},
  "annotation": "Annotation"
}
```

**Response 201**: `QuotePendingEditResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "quote_version_id": "string",
  "editor_user_id": "string",
  "edit_type": "string",
  "target_line_id": "Target Line Id",
  "edit_payload": {},
  "annotation": "Annotation"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/quotes/{id}/pending-edits/test`
**Summary**: Delete all pending edits for current user on this quote (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/quotes/{id}/pending-edits/{edit_id}`
**Summary**: Update a pending edit  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)
- `edit_id` (path, string, required)

**Request body**: `QuotePendingEditUpdate`
```json
{
  "edit_payload": "Edit Payload",
  "annotation": "Annotation"
}
```

**Response 200**: `QuotePendingEditResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "quote_version_id": "string",
  "editor_user_id": "string",
  "edit_type": "string",
  "target_line_id": "Target Line Id",
  "edit_payload": {},
  "annotation": "Annotation"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/quotes/{id}/pending-edits/{edit_id}`
**Summary**: Delete a single pending edit  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)
- `edit_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/quotes/{id}/pending-edits/{edit_id}/test`
**Summary**: Update a pending edit (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)
- `edit_id` (path, string, required)

**Request body**: `QuotePendingEditUpdate`
```json
{
  "edit_payload": "Edit Payload",
  "annotation": "Annotation"
}
```

**Response 200**: `QuotePendingEditResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "quote_version_id": "string",
  "editor_user_id": "string",
  "edit_type": "string",
  "target_line_id": "Target Line Id",
  "edit_payload": {},
  "annotation": "Annotation"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/quotes/{id}/pending-edits/{edit_id}/test`
**Summary**: Delete a single pending edit (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)
- `edit_id` (path, string, required)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/reject`
**Summary**: Reject a pending quote  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteRejectRequest`
```json
{
  "expected_quote_version_id": "Expected Quote Version Id",
  "overall_comment": "string"
}
```

**Response 200**: `QuoteRejectResponse`
```json
{
  "quote_id": "string",
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/reject/test`
**Summary**: Reject a pending quote (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteRejectRequest`
```json
{
  "expected_quote_version_id": "Expected Quote Version Id",
  "overall_comment": "string"
}
```

**Response 200**: `QuoteRejectResponse`
```json
{
  "quote_id": "string",
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/save-as-template`
**Summary**: Save a quote as a reusable template  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteSaveAsTemplateRequest`
```json
{
  "name": "string",
  "category": "Category",
  "style": "Style"
}
```

**Response 201**: `QuoteSaveAsTemplateResponse`
```json
{
  "template_id": "string",
  "name": "string",
  "style": "string",
  "category": "Category",
  "line_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/save-as-template/test`
**Summary**: Save a quote as a template (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Request body**: `QuoteSaveAsTemplateRequest`
```json
{
  "name": "string",
  "category": "Category",
  "style": "Style"
}
```

**Response 201**: `QuoteSaveAsTemplateResponse`
```json
{
  "template_id": "string",
  "name": "string",
  "style": "string",
  "category": "Category",
  "line_count": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/submit-for-approval`
**Summary**: Submit a quote for owner approval  
**Auth**: Required  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `QuoteSubmitForApprovalResponse`
```json
{
  "quote_id": "string",
  "status": "string",
  "submitted_at": "string",
  "submitted_by_user_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{id}/submit-for-approval/test`
**Summary**: Submit a quote for approval (TEST — no auth)  

**Parameters**:
- `id` (path, string, required)

**Response 200**: `QuoteSubmitForApprovalResponse`
```json
{
  "quote_id": "string",
  "status": "string",
  "submitted_at": "string",
  "submitted_by_user_id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{quote_id}`
**Summary**: Get Quote  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `QuoteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "Status Code",
  "subtotal_cents": 0,
  "tax_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/quotes/{quote_id}`
**Summary**: Update Quote  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteUpdate`
```json
{
  "status_id": "Status Id",
  "subtotal_cents": "Subtotal Cents",
  "tax_cents": "Tax Cents",
  "total_cents": "Total Cents",
  "currency": "Currency",
  "expires_at": "Expires At"
}
```

**Response 200**: `QuoteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "Status Code",
  "subtotal_cents": 0,
  "tax_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/convert`
**Summary**: Convert Quote  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Response 201**: `QuoteConvertResponse`
```json
{
  "job_id": "string",
  "quote_id": "string",
  "quote_status": "string",
  "job_status_id": "string",
  "quote_version_id": "Quote Version Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/convert/test`
**Summary**: Convert Quote Test  

**Parameters**:
- `quote_id` (path, string, required)

**Response 201**: `QuoteConvertResponse`
```json
{
  "job_id": "string",
  "quote_id": "string",
  "quote_status": "string",
  "job_status_id": "string",
  "quote_version_id": "Quote Version Id"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{quote_id}/detail`
**Summary**: Get aggregated quote detail for the approval/review surface (PRE-WS3-FIX-01)  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `QuoteDetailResponse`
```json
{
  "id": "string",
  "quote_number": "string",
  "status": "Status",
  "customer_id": "string",
  "customer_name": "Customer Name",
  "site_id": "string",
  "submitted_by_user_id": "Submitted By User Id",
  "submitted_by_name": "Submitted By Name"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{quote_id}/lines`
**Summary**: List Quote Lines  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `Response List Quote Lines Api V1 Quotes  Quote Id  Lines Get`
```json
[
  {
    "id": "string",
    "quote_id": "string",
    "position": 0,
    "qco_line_type_id": "string",
    "pricebook_item_id": "Pricebook Item Id",
    "taxability_code": "Taxability Code",
    "description": "string",
    "quantity": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/lines`
**Summary**: Create Quote Line  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteLineCreate`
```json
{
  "position": 0,
  "qco_line_type_id": "string",
  "pricebook_item_id": "Pricebook Item Id",
  "supplier_id": "Supplier Id",
  "supplier_item_id": "Supplier Item Id",
  "taxability_code": "Taxability Code",
  "description": "string",
  "quantity": "Quantity"
}
```

**Response 201**: `QuoteLineResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "position": 0,
  "qco_line_type_id": "string",
  "pricebook_item_id": "Pricebook Item Id",
  "taxability_code": "Taxability Code",
  "description": "string",
  "quantity": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{quote_id}/lines/test`
**Summary**: List Quote Lines Test  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `Response List Quote Lines Test Api V1 Quotes  Quote Id  Lines Test Get`
```json
[
  {
    "id": "string",
    "quote_id": "string",
    "position": 0,
    "qco_line_type_id": "string",
    "pricebook_item_id": "Pricebook Item Id",
    "taxability_code": "Taxability Code",
    "description": "string",
    "quantity": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/lines/test`
**Summary**: Create Quote Line Test  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteLineCreate`
```json
{
  "position": 0,
  "qco_line_type_id": "string",
  "pricebook_item_id": "Pricebook Item Id",
  "supplier_id": "Supplier Id",
  "supplier_item_id": "Supplier Item Id",
  "taxability_code": "Taxability Code",
  "description": "string",
  "quantity": "Quantity"
}
```

**Response 201**: `QuoteLineResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "position": 0,
  "qco_line_type_id": "string",
  "pricebook_item_id": "Pricebook Item Id",
  "taxability_code": "Taxability Code",
  "description": "string",
  "quantity": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/public-link/revoke`
**Summary**: Revoke Quote Public Link  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `QuoteRevokeLinkResponse`
```json
{
  "id": "string",
  "revoked_at": "string",
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/public-link/revoke/test`
**Summary**: Revoke a quote public link (TEST — no auth)  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `QuoteRevokeLinkResponse`
```json
{
  "id": "string",
  "revoked_at": "string",
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/quotes/{quote_id}/test`
**Summary**: Get Quote Test  

**Parameters**:
- `quote_id` (path, string, required)

**Response 200**: `QuoteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "Status Code",
  "subtotal_cents": 0,
  "tax_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/quotes/{quote_id}/test`
**Summary**: Update Quote Test  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteUpdate`
```json
{
  "status_id": "Status Id",
  "subtotal_cents": "Subtotal Cents",
  "tax_cents": "Tax Cents",
  "total_cents": "Total Cents",
  "currency": "Currency",
  "expires_at": "Expires At"
}
```

**Response 200**: `QuoteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "status_code": "Status Code",
  "subtotal_cents": 0,
  "tax_cents": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/versions`
**Summary**: Create Quote Version  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteVersionCreate`
```json
{
  "presentation_style": "string"
}
```

**Response 201**: `QuoteVersionResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "version_no": 0,
  "snapshot": {},
  "pdf_object_key": "Pdf Object Key",
  "is_active": false,
  "presentation_style": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/versions/test`
**Summary**: Create Quote Version Test  

**Parameters**:
- `quote_id` (path, string, required)

**Request body**: `QuoteVersionCreate`
```json
{
  "presentation_style": "string"
}
```

**Response 201**: `QuoteVersionResponse`
```json
{
  "id": "string",
  "quote_id": "string",
  "version_no": 0,
  "snapshot": {},
  "pdf_object_key": "Pdf Object Key",
  "is_active": false,
  "presentation_style": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/versions/{version_id}/public-link`
**Summary**: Create Public Link  
**Auth**: Required  

**Parameters**:
- `quote_id` (path, string, required)
- `version_id` (path, string, required)

**Request body**: `QuotePublicLinkCreate`
```json
{
  "contact_id": "string",
  "expires_at": "Expires At",
  "max_uses": 0
}
```

**Response 201**: `QuotePublicLinkResponse`
```json
{
  "url": "string",
  "id": "string",
  "quote_id": "string",
  "contact_id": "string",
  "expires_at": "Expires At",
  "signed_token": "Signed Token"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/quotes/{quote_id}/versions/{version_id}/public-link/test`
**Summary**: Create Public Link Test  

**Parameters**:
- `quote_id` (path, string, required)
- `version_id` (path, string, required)

**Request body**: `QuotePublicLinkCreate`
```json
{
  "contact_id": "string",
  "expires_at": "Expires At",
  "max_uses": 0
}
```

**Response 201**: `QuotePublicLinkResponse`
```json
{
  "url": "string",
  "id": "string",
  "quote_id": "string",
  "contact_id": "string",
  "expires_at": "Expires At",
  "signed_token": "Signed Token"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### reports

#### `GET /api/v1/reports/ar-aging`
**Summary**: AR Aging Report  
**Auth**: Required  

**Parameters**:
- `date_from` (query, string, required) — Report period start (unused for aging; required for API consistency)
- `date_to` (query, string, required) — Aging computed as of this date

**Response 200**: `ARAgingReportResponse`
```json
{
  "report_type": "string",
  "as_of_date": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "summary": {
    "current_cents": 0,
    "bucket_31_60_cents": 0,
    "bucket_61_90_cents": 0,
    "bucket_91_plus_cents": 0,
    "total_outstanding_cents": 0
  },
  "data": [
    {
      "customer_id": "...",
      "customer_name": "...",
      "current_cents": "...",
      "bucket_31_60_cents": "...",
      "bucket_61_90_cents": "...",
      "bucket_91_plus_cents": "...",
      "total_outstanding_cents": "...",
      "oldest_invoice_due_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/ar-aging/test`
**Summary**: AR Aging Report (TEST — no auth)  

**Parameters**:
- `date_from` (query, string, required)
- `date_to` (query, string, required)

**Response 200**: `ARAgingReportResponse`
```json
{
  "report_type": "string",
  "as_of_date": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "summary": {
    "current_cents": 0,
    "bucket_31_60_cents": 0,
    "bucket_61_90_cents": 0,
    "bucket_91_plus_cents": 0,
    "total_outstanding_cents": 0
  },
  "data": [
    {
      "customer_id": "...",
      "customer_name": "...",
      "current_cents": "...",
      "bucket_31_60_cents": "...",
      "bucket_61_90_cents": "...",
      "bucket_91_plus_cents": "...",
      "total_outstanding_cents": "...",
      "oldest_invoice_due_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/profitability`
**Summary**: Profitability Report  
**Auth**: Required  

**Parameters**:
- `date_from` (query, string, required) — Report period start (inclusive)
- `date_to` (query, string, required) — Report period end (inclusive)
- `group_by` (query, string, optional, default: job) — Grouping dimension: 'job' | 'customer' | 'site'
- `filter_status` (query, , optional) — Comma-separated job_status.code values

**Response 200**: `ProfitabilityReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "group_key": "...",
      "group_label": "...",
      "customer_name": "...",
      "job_count": "...",
      "quoted_total_cents": "...",
      "actual_labor_cost_cents": "...",
      "actual_material_cost_cents": "...",
      "actual_profit_cents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/profitability/test`
**Summary**: Profitability Report (TEST — no auth)  

**Parameters**:
- `date_from` (query, string, required)
- `date_to` (query, string, required)
- `group_by` (query, string, optional, default: job)
- `filter_status` (query, , optional)

**Response 200**: `ProfitabilityReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "group_key": "...",
      "group_label": "...",
      "customer_name": "...",
      "job_count": "...",
      "quoted_total_cents": "...",
      "actual_labor_cost_cents": "...",
      "actual_material_cost_cents": "...",
      "actual_profit_cents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/revenue`
**Summary**: Revenue Report  
**Auth**: Required  

**Parameters**:
- `date_from` (query, string, required) — Report period start (inclusive)
- `date_to` (query, string, required) — Report period end (inclusive)
- `group_by` (query, string, optional, default: month) — Grouping dimension: 'month' | 'week' | 'quarter'

**Response 200**: `RevenueReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "period_label": "...",
      "period_start": "...",
      "period_end": "...",
      "invoiced_cents": "...",
      "collected_cents": "...",
      "outstanding_cents": "...",
      "invoice_count": "...",
      "payment_count": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/revenue/test`
**Summary**: Revenue Report (TEST — no auth)  

**Parameters**:
- `date_from` (query, string, required)
- `date_to` (query, string, required)
- `group_by` (query, string, optional, default: month)

**Response 200**: `RevenueReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "period_label": "...",
      "period_start": "...",
      "period_end": "...",
      "invoiced_cents": "...",
      "collected_cents": "...",
      "outstanding_cents": "...",
      "invoice_count": "...",
      "payment_count": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/tax-liability`
**Summary**: Tax Liability Report  
**Auth**: Required  

**Parameters**:
- `date_from` (query, string, required) — Report period start (inclusive)
- `date_to` (query, string, required) — Report period end (inclusive)
- `group_by` (query, string, optional, default: month) — Grouping dimension: 'month' | 'quarter'

**Response 200**: `TaxLiabilityReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "period_label": "...",
      "period_start": "...",
      "period_end": "...",
      "invoice_count": "...",
      "total_invoiced_cents": "...",
      "total_tax_cents": "...",
      "effective_tax_rate_pct": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/tax-liability/test`
**Summary**: Tax Liability Report (TEST — no auth)  

**Parameters**:
- `date_from` (query, string, required)
- `date_to` (query, string, required)
- `group_by` (query, string, optional, default: month)

**Response 200**: `TaxLiabilityReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "period_label": "...",
      "period_start": "...",
      "period_end": "...",
      "invoice_count": "...",
      "total_invoiced_cents": "...",
      "total_tax_cents": "...",
      "effective_tax_rate_pct": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/tech-productivity`
**Summary**: Tech Productivity Report  
**Auth**: Required  

**Parameters**:
- `date_from` (query, string, required) — Report period start (inclusive)
- `date_to` (query, string, required) — Report period end (inclusive)
- `group_by` (query, string, optional, default: user) — Grouping dimension: 'user' | 'job_status'
- `user_id` (query, , optional) — Optional UUID filter — restrict to a single technician

**Response 200**: `TechProductivityReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "user_id": "...",
      "user_full_name": "...",
      "jobs_worked": "...",
      "jobs_completed": "...",
      "total_hours_logged": "...",
      "avg_hours_per_job": "...",
      "total_labor_cost_cents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/tech-productivity/test`
**Summary**: Tech Productivity Report (TEST — no auth)  

**Parameters**:
- `date_from` (query, string, required)
- `date_to` (query, string, required)
- `group_by` (query, string, optional, default: user)
- `user_id` (query, , optional)

**Response 200**: `TechProductivityReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "data": [
    {
      "user_id": "...",
      "user_full_name": "...",
      "jobs_worked": "...",
      "jobs_completed": "...",
      "total_hours_logged": "...",
      "avg_hours_per_job": "...",
      "total_labor_cost_cents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/voice-analytics`
**Summary**: Voice Analytics Report  
**Auth**: Required  

**Parameters**:
- `date_from` (query, string, required) — Report period start (inclusive)
- `date_to` (query, string, required) — Report period end (inclusive)
- `group_by` (query, string, optional, default: intent) — Grouping dimension: 'intent' | 'user' | 'day'

**Response 200**: `VoiceAnalyticsReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "summary": {
    "total_commands": 0,
    "successful_commands": 0,
    "success_rate_pct": "Success Rate Pct",
    "avg_whisper_latency_ms": "Avg Whisper Latency Ms",
    "avg_ollama_latency_ms": "Avg Ollama Latency Ms",
    "avg_total_latency_ms": "Avg Total Latency Ms",
    "p95_total_latency_ms": "P95 Total Latency Ms"
  },
  "data": [
    {
      "group_key": "...",
      "group_label": "...",
      "command_count": "...",
      "success_count": "...",
      "success_rate_pct": "...",
      "avg_total_latency_ms": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/voice-analytics/test`
**Summary**: Voice Analytics Report (TEST — no auth)  

**Parameters**:
- `date_from` (query, string, required)
- `date_to` (query, string, required)
- `group_by` (query, string, optional, default: intent)

**Response 200**: `VoiceAnalyticsReportResponse`
```json
{
  "report_type": "string",
  "date_from": "string",
  "date_to": "string",
  "display_mode": "string",
  "row_count": 0,
  "report_chart_threshold": 0,
  "summary": {
    "total_commands": 0,
    "successful_commands": 0,
    "success_rate_pct": "Success Rate Pct",
    "avg_whisper_latency_ms": "Avg Whisper Latency Ms",
    "avg_ollama_latency_ms": "Avg Ollama Latency Ms",
    "avg_total_latency_ms": "Avg Total Latency Ms",
    "p95_total_latency_ms": "P95 Total Latency Ms"
  },
  "data": [
    {
      "group_key": "...",
      "group_label": "...",
      "command_count": "...",
      "success_count": "...",
      "success_rate_pct": "...",
      "avg_total_latency_ms": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/wip`
**Summary**: WIP Report  
**Auth**: Required  

**Parameters**:
- `status` (query, , optional) — Comma-separated job_status.code values (default: scheduled,in_progress)
- `sort` (query, string, optional, default: deviation_pct) — Sort field: deviation_pct | projected_margin_pct | actual_cost_cents | scheduled_start_at
- `order` (query, string, optional, default: desc) — Sort order: asc | desc

**Response 200**: `WipReportResponse`
```json
{
  "report_type": "string",
  "generated_at": "string",
  "margin_target_pct": 0.0,
  "row_count": 0,
  "summary": {
    "active_job_count": 0,
    "total_actual_cost_cents": 0,
    "total_quoted_budget_cents": 0,
    "total_projected_cost_cents": 0,
    "jobs_over_budget_count": 0,
    "jobs_below_margin_target_count": 0
  },
  "rows": [
    {
      "job_id": "...",
      "job_number": "...",
      "title": "...",
      "customer_name": "...",
      "site_name": "...",
      "status_code": "...",
      "scheduled_start_at": "...",
      "quoted_budget_cents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/reports/wip/test`
**Summary**: WIP Report (TEST — no auth)  

**Parameters**:
- `status` (query, , optional) — Comma-separated job_status.code values (default: scheduled,in_progress)
- `sort` (query, string, optional, default: deviation_pct) — Sort field: deviation_pct | projected_margin_pct | actual_cost_cents | scheduled_start_at
- `order` (query, string, optional, default: desc) — Sort order: asc | desc

**Response 200**: `WipReportResponse`
```json
{
  "report_type": "string",
  "generated_at": "string",
  "margin_target_pct": 0.0,
  "row_count": 0,
  "summary": {
    "active_job_count": 0,
    "total_actual_cost_cents": 0,
    "total_quoted_budget_cents": 0,
    "total_projected_cost_cents": 0,
    "jobs_over_budget_count": 0,
    "jobs_below_margin_target_count": 0
  },
  "rows": [
    {
      "job_id": "...",
      "job_number": "...",
      "title": "...",
      "customer_name": "...",
      "site_name": "...",
      "status_code": "...",
      "scheduled_start_at": "...",
      "quoted_budget_cents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### roles

#### `POST /api/v1/permissions/check`
**Summary**: Check User Permission  
**Auth**: Required  

**Request body**: `PermissionCheckRequest`
```json
{
  "permission": "string"
}
```

**Response 200**: `PermissionCheckResponse`
```json
{
  "permission": "string",
  "has_permission": false,
  "user_role": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/permissions/check/test`
**Summary**: Check User Permission Test  

**Request body**: `PermissionCheckRequest`
```json
{
  "permission": "string"
}
```

**Response 200**: `PermissionCheckResponse`
```json
{
  "permission": "string",
  "has_permission": false,
  "user_role": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/roles`
**Summary**: List Roles  
**Auth**: Required  

**Response 200**: `Response List Roles Api V1 Roles Get`
```json
[
  {
    "code": "string",
    "name": "string",
    "description": "Description",
    "permissions": [
      "..."
    ],
    "is_default": false,
    "is_active": false
  }
]
```

---

#### `GET /api/v1/roles/test`
**Summary**: List Roles Test  

**Response 200**: `Response List Roles Test Api V1 Roles Test Get`
```json
[
  {
    "code": "string",
    "name": "string",
    "description": "Description",
    "permissions": [
      "..."
    ],
    "is_default": false,
    "is_active": false
  }
]
```

---

#### `GET /api/v1/users`
**Summary**: List Tenant Users  
**Auth**: Required  

**Response 200**: `Response List Tenant Users Api V1 Users Get`
```json
[
  {
    "user_id": "string",
    "email": "string",
    "role_code": "string",
    "role_name": "string",
    "permissions": [
      "..."
    ],
    "joined_at": "Joined At",
    "is_active": false,
    "first_name": "First Name"
  }
]
```

---

#### `GET /api/v1/users/me/permissions`
**Summary**: Get My Permissions  
**Auth**: Required  

**Response 200**: `UserPermissionsResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "role_code": "string",
  "role_name": "string",
  "permissions": [
    "string"
  ]
}
```

---

#### `GET /api/v1/users/me/permissions/test`
**Summary**: Get My Permissions Test  

**Response 200**: `UserPermissionsResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "role_code": "string",
  "role_name": "string",
  "permissions": [
    "string"
  ]
}
```

---

#### `GET /api/v1/users/test`
**Summary**: List Tenant Users Test  

**Response 200**: `Response List Tenant Users Test Api V1 Users Test Get`
```json
[
  {
    "user_id": "string",
    "email": "string",
    "role_code": "string",
    "role_name": "string",
    "permissions": [
      "..."
    ],
    "joined_at": "Joined At",
    "is_active": false,
    "first_name": "First Name"
  }
]
```

---

#### `POST /api/v1/users/{user_id}/role`
**Summary**: Assign Role  
**Auth**: Required  

**Parameters**:
- `user_id` (path, string, required)

**Request body**: `RoleAssignmentRequest`
```json
{
  "role_code": "string"
}
```

**Response 200**: `RoleAssignmentResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "role_code": "string",
  "role_name": "string",
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/{user_id}/role/test`
**Summary**: Assign Role Test  

**Parameters**:
- `user_id` (path, string, required)

**Request body**: `RoleAssignmentRequest`
```json
{
  "role_code": "string"
}
```

**Response 200**: `RoleAssignmentResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "role_code": "string",
  "role_name": "string",
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### scheduling

#### `GET /api/v1/scheduling/board/stream`
**Summary**: Dispatch board SSE stream (JWT via ?token= query param)  

**Parameters**:
- `token` (query, string, required) — JWT for SSE auth (cannot use headers with EventSource)
- `lastEventId` (query, , optional)

**Response 200**: Successful Response

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/conflict-check`
**Summary**: Check slot feasibility  
**Auth**: Required  

**Request body**: `ConflictCheckRequest`
```json
{
  "tech_user_id": "string",
  "proposed_start": "string",
  "proposed_end": "string",
  "exclude_job_id": "Exclude Job Id"
}
```

**Response 200**: `ConflictCheckResponse`
```json
{
  "is_feasible": false,
  "tech_user_id": "string",
  "proposed_start": "string",
  "proposed_end": "string",
  "conflicts": [
    {
      "conflict_type": "...",
      "description": "...",
      "conflicting_entity_id": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/conflict-check/test`
**Summary**: Check slot feasibility (test — no auth)  

**Request body**: `ConflictCheckRequest`
```json
{
  "tech_user_id": "string",
  "proposed_start": "string",
  "proposed_end": "string",
  "exclude_job_id": "Exclude Job Id"
}
```

**Response 200**: `ConflictCheckResponse`
```json
{
  "is_feasible": false,
  "tech_user_id": "string",
  "proposed_start": "string",
  "proposed_end": "string",
  "conflicts": [
    {
      "conflict_type": "...",
      "description": "...",
      "conflicting_entity_id": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/dispatch-board`
**Summary**: Dispatch board query  
**Auth**: Required  

**Parameters**:
- `start_date` (query, string, required)
- `end_date` (query, string, required)

**Response 200**: `DispatchBoardResponse`
```json
{
  "start_date": "string",
  "end_date": "string",
  "techs": [
    {
      "tech_id": "...",
      "id": "...",
      "name": "...",
      "display_color": "...",
      "avatar_url": "...",
      "jobs": "...",
      "additional_job_commitments": "...",
      "eta_minutes_to_first_job": "..."
    }
  ],
  "unassigned": [
    {
      "id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "site_id": "...",
      "status_id": "...",
      "scheduled_start_at": "...",
      "scheduled_end_at": "...",
      "estimated_duration_minutes": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/dispatch-board/test`
**Summary**: Dispatch board query (test — no auth)  

**Parameters**:
- `start_date` (query, string, required)
- `end_date` (query, string, required)

**Response 200**: `DispatchBoardResponse`
```json
{
  "start_date": "string",
  "end_date": "string",
  "techs": [
    {
      "tech_id": "...",
      "id": "...",
      "name": "...",
      "display_color": "...",
      "avatar_url": "...",
      "jobs": "...",
      "additional_job_commitments": "...",
      "eta_minutes_to_first_job": "..."
    }
  ],
  "unassigned": [
    {
      "id": "...",
      "tenant_id": "...",
      "customer_id": "...",
      "site_id": "...",
      "status_id": "...",
      "scheduled_start_at": "...",
      "scheduled_end_at": "...",
      "estimated_duration_minutes": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/jobs/{job_id}/assignments`
**Summary**: List job assignments  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Assignments Api V1 Scheduling Jobs  Job Id  Assignments Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "user_id": "string",
    "assigned_by_user_id": "string",
    "role": "string",
    "ordinal": 0,
    "assigned_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/jobs/{job_id}/assignments`
**Summary**: Assign tech to job  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobTechAssignmentCreate`
```json
{
  "user_id": "string",
  "role": "string",
  "ordinal": 0,
  "assigned_by_user_id": "Assigned By User Id"
}
```

**Response 201**: `JobTechAssignmentResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "user_id": "string",
  "assigned_by_user_id": "string",
  "role": "string",
  "ordinal": 0,
  "assigned_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/jobs/{job_id}/assignments/test`
**Summary**: List job assignments (test — no auth)  

**Parameters**:
- `job_id` (path, string, required)

**Response 200**: `Response List Assignments Test Api V1 Scheduling Jobs  Job Id  Assignments Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "job_id": "string",
    "user_id": "string",
    "assigned_by_user_id": "string",
    "role": "string",
    "ordinal": 0,
    "assigned_at": "string"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/jobs/{job_id}/assignments/test`
**Summary**: Assign tech to job (test — no auth)  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobTechAssignmentCreate`
```json
{
  "user_id": "string",
  "role": "string",
  "ordinal": 0,
  "assigned_by_user_id": "Assigned By User Id"
}
```

**Response 201**: `JobTechAssignmentResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "job_id": "string",
  "user_id": "string",
  "assigned_by_user_id": "string",
  "role": "string",
  "ordinal": 0,
  "assigned_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}`
**Summary**: Soft-delete job assignment  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `assignment_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}/test`
**Summary**: Soft-delete job assignment (test — no auth)  

**Parameters**:
- `job_id` (path, string, required)
- `assignment_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/jobs/{job_id}/check-conflicts`
**Summary**: Preview conflict check for a proposed job slot  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobCheckConflictRequest`
```json
{
  "tech_user_id": "string",
  "scheduled_start_at": "string",
  "scheduled_end_at": "string"
}
```

**Response 200**: `JobCheckConflictResponse`
```json
{
  "is_feasible": false,
  "conflicts": [
    {}
  ],
  "drive_time_to_next_minutes": "Drive Time To Next Minutes",
  "drive_time_from_prev_minutes": "Drive Time From Prev Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/jobs/{job_id}/check-conflicts/test`
**Summary**: [TEST] Preview conflict check — no auth required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobCheckConflictRequest`
```json
{
  "tech_user_id": "string",
  "scheduled_start_at": "string",
  "scheduled_end_at": "string"
}
```

**Response 200**: `JobCheckConflictResponse`
```json
{
  "is_feasible": false,
  "conflicts": [
    {}
  ],
  "drive_time_to_next_minutes": "Drive Time To Next Minutes",
  "drive_time_from_prev_minutes": "Drive Time From Prev Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/jobs/{job_id}/history`
**Summary**: Get scheduling history for a job  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `ScheduleHistoryResponse`
```json
{
  "job_id": "string",
  "entries": [
    {
      "changed_at": "...",
      "changed_by_user_id": "...",
      "field_name": "...",
      "old_value": "...",
      "new_value": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/jobs/{job_id}/history/test`
**Summary**: Get scheduling history for a job (TEST — no auth)  

**Parameters**:
- `job_id` (path, string, required)
- `limit` (query, integer, optional, default: 50)
- `offset` (query, integer, optional, default: 0)

**Response 200**: `ScheduleHistoryResponse`
```json
{
  "job_id": "string",
  "entries": [
    {
      "changed_at": "...",
      "changed_by_user_id": "...",
      "field_name": "...",
      "old_value": "...",
      "new_value": "..."
    }
  ],
  "total": 0,
  "limit": 0,
  "offset": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/jobs/{job_id}/move`
**Summary**: Move/reassign a job (optimistic locking)  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobMoveRequest`
```json
{
  "tech_user_id": "string",
  "scheduled_start_at": "string",
  "scheduled_end_at": "string",
  "expected_job_version": 0,
  "expected_assignment_version": "Expected Assignment Version"
}
```

**Response 200**: `JobMoveResponse`
```json
{
  "job_id": "string",
  "job_version": 0,
  "assignment_id": "Assignment Id",
  "assignment_version": "Assignment Version",
  "tech_user_id": "string",
  "scheduled_start_at": "string",
  "scheduled_end_at": "string",
  "conflicts": [
    {}
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/jobs/{job_id}/move/test`
**Summary**: [TEST] Move/reassign a job — no auth required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobMoveRequest`
```json
{
  "tech_user_id": "string",
  "scheduled_start_at": "string",
  "scheduled_end_at": "string",
  "expected_job_version": 0,
  "expected_assignment_version": "Expected Assignment Version"
}
```

**Response 200**: `JobMoveResponse`
```json
{
  "job_id": "string",
  "job_version": 0,
  "assignment_id": "Assignment Id",
  "assignment_version": "Assignment Version",
  "tech_user_id": "string",
  "scheduled_start_at": "string",
  "scheduled_end_at": "string",
  "conflicts": [
    {}
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/scheduling/jobs/{job_id}/schedule`
**Summary**: Update job schedule  
**Auth**: Required  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobScheduleUpdate`
```json
{
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes",
  "external_calendar_event_id": "External Calendar Event Id"
}
```

**Response 200**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/scheduling/jobs/{job_id}/schedule/test`
**Summary**: Update job schedule (test — no auth)  

**Parameters**:
- `job_id` (path, string, required)

**Request body**: `JobScheduleUpdate`
```json
{
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes",
  "external_calendar_event_id": "External Calendar Event Id"
}
```

**Response 200**: `JobResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "site_id": "string",
  "status_id": "string",
  "scheduled_start_at": "Scheduled Start At",
  "scheduled_end_at": "Scheduled End At",
  "estimated_duration_minutes": "Estimated Duration Minutes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/tech-availability/`
**Summary**: List tech availability  
**Auth**: Required  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)
- `user_id` (query, , optional)

**Response 200**: `Response List Tech Availability Api V1 Scheduling Tech Availability  Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "user_id": "string",
    "availability_type": "string",
    "starts_at": "Starts At",
    "ends_at": "Ends At",
    "recurrence_rrule": "Recurrence Rrule",
    "notes": "Notes"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/tech-availability/`
**Summary**: Create tech availability  
**Auth**: Required  

**Request body**: `TechAvailabilityCreate`
```json
{
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 201**: `TechAvailabilityResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/tech-availability/test`
**Summary**: List tech availability (test — no auth)  

**Parameters**:
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)
- `user_id` (query, , optional)

**Response 200**: `Response List Tech Availability Test Api V1 Scheduling Tech Availability Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "user_id": "string",
    "availability_type": "string",
    "starts_at": "Starts At",
    "ends_at": "Ends At",
    "recurrence_rrule": "Recurrence Rrule",
    "notes": "Notes"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/scheduling/tech-availability/test`
**Summary**: Create tech availability (test — no auth)  

**Request body**: `TechAvailabilityCreate`
```json
{
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 201**: `TechAvailabilityResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/tech-availability/{record_id}`
**Summary**: Get tech availability record  
**Auth**: Required  

**Parameters**:
- `record_id` (path, string, required)

**Response 200**: `TechAvailabilityResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/scheduling/tech-availability/{record_id}`
**Summary**: Update tech availability record  
**Auth**: Required  

**Parameters**:
- `record_id` (path, string, required)

**Request body**: `TechAvailabilityUpdate`
```json
{
  "availability_type": "Availability Type",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes",
  "is_active": "Is Active"
}
```

**Response 200**: `TechAvailabilityResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/scheduling/tech-availability/{record_id}`
**Summary**: Soft-delete tech availability record  
**Auth**: Required  

**Parameters**:
- `record_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/scheduling/tech-availability/{record_id}/test`
**Summary**: Get tech availability (test — no auth)  

**Parameters**:
- `record_id` (path, string, required)

**Response 200**: `TechAvailabilityResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/scheduling/tech-availability/{record_id}/test`
**Summary**: Update tech availability (test — no auth)  

**Parameters**:
- `record_id` (path, string, required)

**Request body**: `TechAvailabilityUpdate`
```json
{
  "availability_type": "Availability Type",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes",
  "is_active": "Is Active"
}
```

**Response 200**: `TechAvailabilityResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "user_id": "string",
  "availability_type": "string",
  "starts_at": "Starts At",
  "ends_at": "Ends At",
  "recurrence_rrule": "Recurrence Rrule",
  "notes": "Notes"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/scheduling/tech-availability/{record_id}/test`
**Summary**: Soft-delete tech availability (test — no auth)  

**Parameters**:
- `record_id` (path, string, required)

**Response 200**: `SoftDeleteResponse`
```json
{
  "message": "string",
  "id": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### settings

#### `GET /api/v1/settings`
**Summary**: Get active labor rates  
**Auth**: Required  

**Parameters**:
- `skill_level_code` (query, , optional)

**Response 200**: `Response Get Active Labor Rates Api V1 Settings Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings`
**Summary**: Create or supersede a labor rate  
**Auth**: Required  

**Request body**: `Payload`
```json
{}
```

**Response 201**: `Response Create Labor Rate Api V1 Settings Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/10dlc-profile`
**Summary**: Get 10DLC business profile  
**Auth**: Required  

**Response 200**: `Tenant10DlcProfileResponse`
```json
{
  "tenant_id": "string",
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein_masked": "Ein Masked",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State"
}
```

---

#### `PUT /api/v1/settings/10dlc-profile`
**Summary**: Create or update 10DLC business profile  
**Auth**: Required  

**Request body**: `Tenant10DlcProfileRequest`
```json
{
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein": "Ein",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State",
  "hq_postal_code": "Hq Postal Code"
}
```

**Response 200**: `Tenant10DlcProfileResponse`
```json
{
  "tenant_id": "string",
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein_masked": "Ein Masked",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/10dlc-profile/test`
**Summary**: [TEST] Get 10DLC profile — no auth  

**Response 200**: `Tenant10DlcProfileResponse`
```json
{
  "tenant_id": "string",
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein_masked": "Ein Masked",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State"
}
```

---

#### `PUT /api/v1/settings/10dlc-profile/test`
**Summary**: [TEST] Upsert 10DLC profile — no auth  

**Request body**: `Tenant10DlcProfileRequest`
```json
{
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein": "Ein",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State",
  "hq_postal_code": "Hq Postal Code"
}
```

**Response 200**: `Tenant10DlcProfileResponse`
```json
{
  "tenant_id": "string",
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein_masked": "Ein Masked",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/background-sync-policy`
**Summary**: Get tenant background sync policy for mobile app  
**Auth**: Required  

**Response 200**: `BackgroundSyncPolicyResponse`
```json
{
  "background_sync_enabled": false,
  "background_sync_wifi_only": false,
  "background_sync_battery_floor_pct": 0,
  "background_sync_push_interval_minutes": 0
}
```

---

#### `GET /api/v1/settings/background-sync-policy/test`
**Summary**: [TEST] Get tenant background sync policy — no auth required  

**Response 200**: `BackgroundSyncPolicyResponse`
```json
{
  "background_sync_enabled": false,
  "background_sync_wifi_only": false,
  "background_sync_battery_floor_pct": 0,
  "background_sync_push_interval_minutes": 0
}
```

---

#### `GET /api/v1/settings/billing/payment-contact`
**Summary**: Get billing payment-contact (phone + email)  
**Auth**: Required  

**Response 200**: `PaymentContactResponse`
```json
{
  "billing_contact_phone": "Billing Contact Phone",
  "billing_contact_email": "Billing Contact Email"
}
```

---

#### `PATCH /api/v1/settings/billing/payment-contact`
**Summary**: Update billing payment-contact (phone + email)  
**Auth**: Required  

**Request body**: `PaymentContactUpdateRequest`
```json
{
  "billing_contact_phone": "Billing Contact Phone",
  "billing_contact_email": "Billing Contact Email"
}
```

**Response 200**: `PaymentContactResponse`
```json
{
  "billing_contact_phone": "Billing Contact Phone",
  "billing_contact_email": "Billing Contact Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/billing/payment-contact/test`
**Summary**: [TEST] Get billing payment-contact  

**Response 200**: `PaymentContactResponse`
```json
{
  "billing_contact_phone": "Billing Contact Phone",
  "billing_contact_email": "Billing Contact Email"
}
```

---

#### `PATCH /api/v1/settings/billing/payment-contact/test`
**Summary**: [TEST] Update billing payment-contact  

**Request body**: `PaymentContactUpdateRequest`
```json
{
  "billing_contact_phone": "Billing Contact Phone",
  "billing_contact_email": "Billing Contact Email"
}
```

**Response 200**: `PaymentContactResponse`
```json
{
  "billing_contact_phone": "Billing Contact Phone",
  "billing_contact_email": "Billing Contact Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/billing/stripe-connect`
**Summary**: Disconnect Stripe connected account  
**Auth**: Required  

**Response 200**: `StripeConnectDisconnectResponse`
```json
{
  "disconnected": false,
  "message": "string"
}
```

---

#### `POST /api/v1/settings/billing/stripe-connect/onboard`
**Summary**: Generate Stripe Account Link for onboarding  
**Auth**: Required  

**Response 200**: `StripeConnectOnboardResponse`
```json
{
  "account_link_url": "string",
  "expires_at": 0
}
```

---

#### `POST /api/v1/settings/billing/stripe-connect/onboard/test`
**Summary**: [TEST] Generate Stripe Account Link for onboarding  

**Response 200**: `StripeConnectOnboardResponse`
```json
{
  "account_link_url": "string",
  "expires_at": 0
}
```

---

#### `GET /api/v1/settings/billing/stripe-connect/status`
**Summary**: Get Stripe Connect account status  
**Auth**: Required  

**Response 200**: `StripeConnectStatusResponse`
```json
{
  "connected": false,
  "account_id": "Account Id",
  "account_name": "Account Name",
  "charges_enabled": false,
  "payouts_enabled": false
}
```

---

#### `GET /api/v1/settings/billing/stripe-connect/status/test`
**Summary**: [TEST] Get Stripe Connect account status  

**Response 200**: `StripeConnectStatusResponse`
```json
{
  "connected": false,
  "account_id": "Account Id",
  "account_name": "Account Name",
  "charges_enabled": false,
  "payouts_enabled": false
}
```

---

#### `DELETE /api/v1/settings/billing/stripe-connect/test`
**Summary**: [TEST] Disconnect Stripe connected account  

**Response 200**: `StripeConnectDisconnectResponse`
```json
{
  "disconnected": false,
  "message": "string"
}
```

---

#### `PUT /api/v1/settings/bulk`
**Summary**: Atomically write multiple tenant settings in one commit  
**Auth**: Required  

**Request body**: `BulkSettingWriteRequest`
```json
{
  "values": {}
}
```

**Response 200**: `BulkSettingWriteResponse`
```json
{
  "updated": [
    "string"
  ],
  "results": [
    {
      "key": "...",
      "value": "...",
      "effective_value": "...",
      "scope": "...",
      "updated_at": "...",
      "pending_quote_count": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/catalog`
**Summary**: Get full settings catalog with resolved effective values  
**Auth**: Required  

**Response 200**: `CatalogResponse`
```json
{
  "settings": [
    {
      "key": "...",
      "label": "...",
      "description": "...",
      "sub_surface_path": "...",
      "data_type": "...",
      "validation_rules": "...",
      "system_default": "...",
      "current_effective_value": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/email-branding`
**Summary**: Get Email Branding  
**Auth**: Required  

**Response 200**: `EmailBrandingResponse`
```json
{
  "tenant_id": "string",
  "logo_url": "Logo Url",
  "brand_color_hex": "Brand Color Hex",
  "email_signature": "Email Signature",
  "custom_footer": "Custom Footer"
}
```

---

#### `PATCH /api/v1/settings/email-branding`
**Summary**: Update Email Branding  
**Auth**: Required  

**Request body**: `EmailBrandingUpdate`
```json
{
  "logo_s3_path": "Logo S3 Path",
  "brand_color_hex": "Brand Color Hex",
  "email_signature": "Email Signature",
  "custom_footer": "Custom Footer"
}
```

**Response 200**: `EmailBrandingResponse`
```json
{
  "tenant_id": "string",
  "logo_url": "Logo Url",
  "brand_color_hex": "Brand Color Hex",
  "email_signature": "Email Signature",
  "custom_footer": "Custom Footer"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings/email-branding/logo-upload-url`
**Summary**: Get Logo Upload Url  
**Auth**: Required  

**Request body**: `LogoUploadUrlRequest`
```json
{
  "content_type": "string",
  "file_size_bytes": 0
}
```

**Response 200**: `LogoUploadUrlResponse`
```json
{
  "upload_url": "string",
  "s3_path": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings/email-branding/preview`
**Summary**: Preview Email Branding  
**Auth**: Required  

**Request body**: `PreviewRequest`
```json
{
  "template_id": "string"
}
```

**Response 200**: `PreviewResponse`
```json
{
  "subject": "string",
  "body_html": "string",
  "body_plain": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/email-branding/test`
**Summary**: Get Email Branding Test  

**Response 200**: `EmailBrandingResponse`
```json
{
  "tenant_id": "string",
  "logo_url": "Logo Url",
  "brand_color_hex": "Brand Color Hex",
  "email_signature": "Email Signature",
  "custom_footer": "Custom Footer"
}
```

---

#### `PATCH /api/v1/settings/email-branding/test`
**Summary**: Update Email Branding Test  

**Request body**: `EmailBrandingUpdate`
```json
{
  "logo_s3_path": "Logo S3 Path",
  "brand_color_hex": "Brand Color Hex",
  "email_signature": "Email Signature",
  "custom_footer": "Custom Footer"
}
```

**Response 200**: `EmailBrandingResponse`
```json
{
  "tenant_id": "string",
  "logo_url": "Logo Url",
  "brand_color_hex": "Brand Color Hex",
  "email_signature": "Email Signature",
  "custom_footer": "Custom Footer"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings/email-branding/test-send`
**Summary**: Test Send Email  
**Auth**: Required  

**Response 200**: `TestSendResponse`
```json
{
  "status": "string",
  "to": "string"
}
```

---

#### `POST /api/v1/settings/email-branding/test/logo-upload-url`
**Summary**: Get Logo Upload Url Test  

**Request body**: `LogoUploadUrlRequest`
```json
{
  "content_type": "string",
  "file_size_bytes": 0
}
```

**Response 200**: `LogoUploadUrlResponse`
```json
{
  "upload_url": "string",
  "s3_path": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings/email-branding/test/preview`
**Summary**: Preview Email Branding Test  

**Request body**: `PreviewRequest`
```json
{
  "template_id": "string"
}
```

**Response 200**: `PreviewResponse`
```json
{
  "subject": "string",
  "body_html": "string",
  "body_plain": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/loto-policy`
**Summary**: Get tenant LOTO confirmation-required policy  
**Auth**: Required  

**Response 200**: `LotoPolicyResponse`
```json
{
  "loto_confirmation_required": false
}
```

---

#### `GET /api/v1/settings/loto-policy/test`
**Summary**: [TEST] Get tenant LOTO policy — no auth required  

**Response 200**: `LotoPolicyResponse`
```json
{
  "loto_confirmation_required": false
}
```

---

#### `GET /api/v1/settings/markups`
**Summary**: List Active Category Markups  
**Auth**: Required  

**Response 200**: `TenantMarkupVersionListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "job_expense_category_code": "...",
      "markup_pct": "...",
      "markup_amt_cents": "...",
      "valid_period_lower": "...",
      "valid_period_upper": "...",
      "recorded_at": "..."
    }
  ],
  "total": 0
}
```

---

#### `POST /api/v1/settings/markups`
**Summary**: Create/Update Markup via Temporal Supersession  
**Auth**: Required  

**Request body**: `TenantMarkupVersionCreate`
```json
{
  "job_expense_category_code": "string",
  "markup_pct": 0.0,
  "markup_amt_cents": "Markup Amt Cents",
  "effective_from": "string"
}
```

**Response 201**: `TenantMarkupVersionResponse`
```json
{
  "id": 0,
  "tenant_id": "string",
  "job_expense_category_code": "string",
  "markup_pct": 0.0,
  "markup_amt_cents": "Markup Amt Cents",
  "valid_period_lower": "string",
  "valid_period_upper": "Valid Period Upper",
  "recorded_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/markups/test`
**Summary**: [TEST] List Active Category Markups  

**Parameters**:
- `test_tenant_id` (query, , optional)

**Response 200**: `TenantMarkupVersionListResponse`
```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "job_expense_category_code": "...",
      "markup_pct": "...",
      "markup_amt_cents": "...",
      "valid_period_lower": "...",
      "valid_period_upper": "...",
      "recorded_at": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings/markups/test`
**Summary**: [TEST] Create/Update Markup via Temporal Supersession  

**Parameters**:
- `test_tenant_id` (query, , optional)

**Request body**: `TenantMarkupVersionCreate`
```json
{
  "job_expense_category_code": "string",
  "markup_pct": 0.0,
  "markup_amt_cents": "Markup Amt Cents",
  "effective_from": "string"
}
```

**Response 201**: `TenantMarkupVersionResponse`
```json
{
  "id": 0,
  "tenant_id": "string",
  "job_expense_category_code": "string",
  "markup_pct": 0.0,
  "markup_amt_cents": "Markup Amt Cents",
  "valid_period_lower": "string",
  "valid_period_upper": "Valid Period Upper",
  "recorded_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/markups/{category_code}/history`
**Summary**: Get Markup History for Category  
**Auth**: Required  

**Parameters**:
- `category_code` (path, string, required)

**Response 200**: `TenantMarkupVersionHistoryResponse`
```json
{
  "category_code": "string",
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "job_expense_category_code": "...",
      "markup_pct": "...",
      "markup_amt_cents": "...",
      "valid_period_lower": "...",
      "valid_period_upper": "...",
      "recorded_at": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/markups/{category_code}/history/test`
**Summary**: [TEST] Get Markup History for Category  

**Parameters**:
- `category_code` (path, string, required)
- `test_tenant_id` (query, , optional)

**Response 200**: `TenantMarkupVersionHistoryResponse`
```json
{
  "category_code": "string",
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "job_expense_category_code": "...",
      "markup_pct": "...",
      "markup_amt_cents": "...",
      "valid_period_lower": "...",
      "valid_period_upper": "...",
      "recorded_at": "..."
    }
  ],
  "total": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/tenant/mfa-required`
**Summary**: Get Mfa Policy  
**Auth**: Required  

**Response 200**: `MfaPolicyResponse`
```json
{
  "tenant_mfa_required": false,
  "grace_period_starts_at": "Grace Period Starts At",
  "grace_period_days": 0
}
```

---

#### `PUT /api/v1/settings/tenant/mfa-required`
**Summary**: Put Mfa Policy  
**Auth**: Required  

**Request body**: `MfaPolicyRequest`
```json
{
  "enabled": false,
  "grace_period_days": "Grace Period Days"
}
```

**Response 200**: `MfaPolicyResponse`
```json
{
  "tenant_mfa_required": false,
  "grace_period_starts_at": "Grace Period Starts At",
  "grace_period_days": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/tenant/mfa-required/test`
**Summary**: Get Mfa Policy Test  

**Response 200**: `MfaPolicyResponse`
```json
{
  "tenant_mfa_required": false,
  "grace_period_starts_at": "Grace Period Starts At",
  "grace_period_days": 0
}
```

---

#### `PUT /api/v1/settings/tenant/mfa-required/test`
**Summary**: Put Mfa Policy Test  

**Request body**: `MfaPolicyRequest`
```json
{
  "enabled": false,
  "grace_period_days": "Grace Period Days"
}
```

**Response 200**: `MfaPolicyResponse`
```json
{
  "tenant_mfa_required": false,
  "grace_period_starts_at": "Grace Period Starts At",
  "grace_period_days": 0
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/tenant/voice-persona-tone`
**Summary**: Get Tenant Voice Persona Tone  
**Auth**: Required  

**Response 200**: `VoicePersonaToneTenantResponse`
```json
{
  "tenant_default": "Tenant Default",
  "tenant_default_scope": "string",
  "system_default": "string",
  "user_override_policy": false,
  "available_tones": [
    "string"
  ],
  "preview_audio_urls": {}
}
```

---

#### `PUT /api/v1/settings/tenant/voice-persona-tone`
**Summary**: Set Tenant Voice Persona Tone  
**Auth**: Required  

**Request body**: `VoicePersonaToneTenantRequest`
```json
{
  "value": "string"
}
```

**Response 200**: `VoicePersonaToneWriteResponse`
```json
{
  "setting_key": "string",
  "value": "Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/tenant/voice-persona-tone`
**Summary**: Delete Tenant Voice Persona Tone  
**Auth**: Required  

**Response 204**: Successful Response

---

#### `PUT /api/v1/settings/tenant/voice-persona-tone-user-override-allowed`
**Summary**: Set User Override Policy  
**Auth**: Required  

**Request body**: `VoicePersonaToneUserOverridePolicyRequest`
```json
{
  "value": false
}
```

**Response 200**: `VoicePersonaToneWriteResponse`
```json
{
  "setting_key": "string",
  "value": "Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/settings/tenant/voice-persona-tone-user-override-allowed/test`
**Summary**: Set User Override Policy Test  

**Request body**: `VoicePersonaToneUserOverridePolicyRequest`
```json
{
  "value": false
}
```

**Response 200**: `VoicePersonaToneWriteResponse`
```json
{
  "setting_key": "string",
  "value": "Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/tenant/voice-persona-tone/test`
**Summary**: Get Tenant Voice Persona Tone Test  

**Response 200**: `VoicePersonaToneTenantResponse`
```json
{
  "tenant_default": "Tenant Default",
  "tenant_default_scope": "string",
  "system_default": "string",
  "user_override_policy": false,
  "available_tones": [
    "string"
  ],
  "preview_audio_urls": {}
}
```

---

#### `PUT /api/v1/settings/tenant/voice-persona-tone/test`
**Summary**: Set Tenant Voice Persona Tone Test  

**Request body**: `VoicePersonaToneTenantRequest`
```json
{
  "value": "string"
}
```

**Response 200**: `VoicePersonaToneWriteResponse`
```json
{
  "setting_key": "string",
  "value": "Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/tenant/voice-persona-tone/test`
**Summary**: Delete Tenant Voice Persona Tone Test  

**Response 204**: Successful Response

---

#### `GET /api/v1/settings/test`
**Summary**: Get active labor rates (TEST — no auth)  

**Parameters**:
- `skill_level_code` (query, , optional)

**Response 200**: `Response Get Active Labor Rates Test Api V1 Settings Test Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/settings/test`
**Summary**: Create or supersede a labor rate (TEST — no auth)  

**Request body**: `Payload`
```json
{}
```

**Response 201**: `Response Create Labor Rate Test Api V1 Settings Test Post`

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/settings/test/bulk`
**Summary**: [TEST] Bulk write tenant settings — no auth required  

**Request body**: `BulkSettingWriteRequest`
```json
{
  "values": {}
}
```

**Response 200**: `BulkSettingWriteResponse`
```json
{
  "updated": [
    "string"
  ],
  "results": [
    {
      "key": "...",
      "value": "...",
      "effective_value": "...",
      "scope": "...",
      "updated_at": "...",
      "pending_quote_count": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/test/catalog`
**Summary**: [TEST] Get settings catalog — no auth required  

**Response 200**: `CatalogResponse`
```json
{
  "settings": [
    {
      "key": "...",
      "label": "...",
      "description": "...",
      "sub_surface_path": "...",
      "data_type": "...",
      "validation_rules": "...",
      "system_default": "...",
      "current_effective_value": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/settings/test/{key}`
**Summary**: [TEST] Write tenant setting — no auth required  

**Parameters**:
- `key` (path, string, required)

**Request body**: `TenantSettingWriteRequest`
```json
{
  "value": "Value",
  "expected_updated_at": "Expected Updated At"
}
```

**Response 200**: `TenantSettingWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string",
  "pending_quote_count": "Pending Quote Count"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/test/{key}/effective`
**Summary**: [TEST] Get effective setting value — no auth required  

**Parameters**:
- `key` (path, string, required)

**Response 200**: `EffectiveSettingResponse`
```json
{
  "key": "string",
  "value": "Value",
  "scope": "string",
  "tenant_override_exists": false,
  "user_override_exists": false,
  "allows_user_override": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/test/{key}/tenant-override`
**Summary**: [TEST] Revert tenant setting override — no auth required  

**Parameters**:
- `key` (path, string, required)

**Response 200**: `TenantSettingWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string",
  "pending_quote_count": "Pending Quote Count"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/settings/test/{key}/user-override`
**Summary**: [TEST] Write user setting override — no auth required  

**Parameters**:
- `key` (path, string, required)

**Request body**: `UserOverrideWriteRequest`
```json
{
  "value": "Value"
}
```

**Response 200**: `UserOverrideWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/test/{key}/user-override`
**Summary**: [TEST] Delete user setting override — no auth required  

**Parameters**:
- `key` (path, string, required)

**Response 200**: `UserOverrideWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/voice-persona-tone`
**Summary**: Get Effective Voice Persona Tone  
**Auth**: Required  

**Response 200**: `VoicePersonaToneEffectiveResponse`
```json
{
  "effective_tone": "string",
  "effective_scope": "string",
  "user_override": "User Override",
  "tenant_default": "Tenant Default",
  "system_default": "string",
  "user_override_allowed": false,
  "available_tones": [
    "string"
  ],
  "preview_audio_urls": {}
}
```

---

#### `PUT /api/v1/settings/voice-persona-tone`
**Summary**: Set User Voice Persona Tone  
**Auth**: Required  

**Request body**: `VoicePersonaToneUserRequest`
```json
{
  "value": "string"
}
```

**Response 200**: `VoicePersonaToneWriteResponse`
```json
{
  "setting_key": "string",
  "value": "Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/voice-persona-tone`
**Summary**: Delete User Voice Persona Tone  
**Auth**: Required  

**Response 204**: Successful Response

---

#### `GET /api/v1/settings/voice-persona-tone/test`
**Summary**: Get Effective Voice Persona Tone Test  

**Response 200**: `VoicePersonaToneEffectiveResponse`
```json
{
  "effective_tone": "string",
  "effective_scope": "string",
  "user_override": "User Override",
  "tenant_default": "Tenant Default",
  "system_default": "string",
  "user_override_allowed": false,
  "available_tones": [
    "string"
  ],
  "preview_audio_urls": {}
}
```

---

#### `PUT /api/v1/settings/voice-persona-tone/test`
**Summary**: Set User Voice Persona Tone Test  

**Request body**: `VoicePersonaToneUserRequest`
```json
{
  "value": "string"
}
```

**Response 200**: `VoicePersonaToneWriteResponse`
```json
{
  "setting_key": "string",
  "value": "Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/voice-persona-tone/test`
**Summary**: Delete User Voice Persona Tone Test  

**Response 204**: Successful Response

---

#### `PUT /api/v1/settings/{key}`
**Summary**: Write a tenant-level setting override  
**Auth**: Required  

**Parameters**:
- `key` (path, string, required)

**Request body**: `TenantSettingWriteRequest`
```json
{
  "value": "Value",
  "expected_updated_at": "Expected Updated At"
}
```

**Response 200**: `TenantSettingWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string",
  "pending_quote_count": "Pending Quote Count"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/{key}/effective`
**Summary**: Get resolved effective value for a single setting key  
**Auth**: Required  

**Parameters**:
- `key` (path, string, required)
- `user_id` (query, , optional)

**Response 200**: `EffectiveSettingResponse`
```json
{
  "key": "string",
  "value": "Value",
  "scope": "string",
  "tenant_override_exists": false,
  "user_override_exists": false,
  "allows_user_override": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/{key}/tenant-override`
**Summary**: Revert a tenant setting override to its system default  
**Auth**: Required  

**Parameters**:
- `key` (path, string, required)

**Response 200**: `TenantSettingWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string",
  "pending_quote_count": "Pending Quote Count"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/settings/{key}/user-override`
**Summary**: Write a per-user setting override  
**Auth**: Required  

**Parameters**:
- `key` (path, string, required)

**Request body**: `UserOverrideWriteRequest`
```json
{
  "value": "Value"
}
```

**Response 200**: `UserOverrideWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `DELETE /api/v1/settings/{key}/user-override`
**Summary**: Remove a per-user setting override (revert to tenant/system default)  
**Auth**: Required  

**Parameters**:
- `key` (path, string, required)

**Response 200**: `UserOverrideWriteResponse`
```json
{
  "key": "string",
  "value": "Value",
  "effective_value": "Effective Value",
  "scope": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/{skill_level_code}/history`
**Summary**: Get historical labor rates for a skill level  
**Auth**: Required  

**Parameters**:
- `skill_level_code` (path, string, required)

**Response 200**: `Response Get Labor Rate History Api V1 Settings  Skill Level Code  History Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/settings/{skill_level_code}/history/test`
**Summary**: Get historical labor rates for a skill level (TEST — no auth)  

**Parameters**:
- `skill_level_code` (path, string, required)

**Response 200**: `Response Get Labor Rate History Test Api V1 Settings  Skill Level Code  History Test Get`
```json
[
  {}
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenant-site`
**Summary**: Get tenant site configuration + defaults  
**Auth**: Required  

**Response 200**: `TenantSiteGetResponse`
```json
{
  "configured": false,
  "site": "object",
  "defaults": {
    "display_name": "Display Name",
    "display_name_source": "Display Name Source",
    "public_email": "Public Email",
    "public_email_source": "Public Email Source",
    "public_phone": "Public Phone",
    "public_phone_source": "Public Phone Source",
    "public_city": "Public City",
    "public_city_source": "Public City Source"
  }
}
```

---

#### `PUT /api/v1/tenant-site`
**Summary**: Create or update tenant site draft  
**Auth**: Required  

**Parameters**:
- `idempotency_key` (query, , optional)

**Request body**: `TenantSiteUpsertRequest`
```json
{
  "site_kind": "string",
  "slug": "string",
  "display_name": "Display Name",
  "tagline": "Tagline",
  "public_email": "Public Email",
  "public_phone": "Public Phone",
  "public_city": "Public City",
  "public_state": "Public State"
}
```

**Response 200**: `TenantSiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "slug": "string",
  "site_kind": "string",
  "status": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenant-site/publish`
**Summary**: Publish tenant site  
**Auth**: Required  

**Request body**: `PublishRequest`
```json
{
  "confirm_website_overwrite": false
}
```

**Response 200**: `PublishResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "slug": "string",
  "site_kind": "string",
  "status": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenant-site/publish/test`
**Summary**: [TEST] Publish tenant site — no auth  

**Request body**: `PublishRequest`
```json
{
  "confirm_website_overwrite": false
}
```

**Response 200**: `PublishResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "slug": "string",
  "site_kind": "string",
  "status": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenant-site/slug-availability`
**Summary**: Check slug availability  
**Auth**: Required  

**Parameters**:
- `slug` (query, string, required)

**Response 200**: `SlugAvailabilityResponse`
```json
{
  "available": false,
  "reason": "Reason",
  "suggestion": "Suggestion"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenant-site/test`
**Summary**: [TEST] Upsert tenant site draft — no auth  

**Request body**: `TenantSiteUpsertRequest`
```json
{
  "site_kind": "string",
  "slug": "string",
  "display_name": "Display Name",
  "tagline": "Tagline",
  "public_email": "Public Email",
  "public_phone": "Public Phone",
  "public_city": "Public City",
  "public_state": "Public State"
}
```

**Response 200**: `TenantSiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "slug": "string",
  "site_kind": "string",
  "status": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenant-site/unpublish`
**Summary**: Unpublish tenant site  
**Auth**: Required  

**Response 200**: `UnpublishResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "slug": "string",
  "site_kind": "string",
  "status": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email"
}
```

---

#### `POST /api/v1/tenant-site/unpublish/test`
**Summary**: [TEST] Unpublish tenant site — no auth  

**Response 200**: `UnpublishResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "slug": "string",
  "site_kind": "string",
  "status": "string",
  "display_name": "string",
  "tagline": "Tagline",
  "public_email": "Public Email"
}
```

---

### signup

#### `POST /api/v1/signup/`
**Summary**: Initiate Signup Route  

**Request body**: `SignupInitiateRequest`
```json
{
  "business_name": "string",
  "trade": "string",
  "business_size": "string",
  "zip": "string",
  "time_zone": "string",
  "owner_email": "string",
  "owner_first_name": "string",
  "owner_last_name": "string"
}
```

**Response 201**: `SignupInitiateResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "owner_email": "string",
  "credential_pending": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/test`
**Summary**: Initiate Signup Test  

**Request body**: `SignupInitiateRequest`
```json
{
  "business_name": "string",
  "trade": "string",
  "business_size": "string",
  "zip": "string",
  "time_zone": "string",
  "owner_email": "string",
  "owner_first_name": "string",
  "owner_last_name": "string"
}
```

**Response 201**: `SignupInitiateResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "owner_email": "string",
  "credential_pending": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/{tenant_id}/legal/accept`
**Summary**: Accept Legal Document  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `LegalAcceptRequest`
```json
{
  "document_type": "string",
  "document_version_hash": "string",
  "accepted_at": "string"
}
```

**Response 201**: `LegalAcceptResponse`
```json
{
  "acceptance_id": "string",
  "document_type": "string",
  "accepted_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/{tenant_id}/legal/accept/test`
**Summary**: Accept Legal Document Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `LegalAcceptRequest`
```json
{
  "document_type": "string",
  "document_version_hash": "string",
  "accepted_at": "string"
}
```

**Response 201**: `LegalAcceptResponse`
```json
{
  "acceptance_id": "string",
  "document_type": "string",
  "accepted_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/signup/{tenant_id}/legal/required`
**Summary**: Get Legal Required  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `LegalRequiredResponse`
```json
{
  "required_documents": [
    {
      "document_type": "...",
      "current_version_hash": "...",
      "already_accepted": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/signup/{tenant_id}/legal/required/test`
**Summary**: Get Legal Required Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `LegalRequiredResponse`
```json
{
  "required_documents": [
    {
      "document_type": "...",
      "current_version_hash": "...",
      "already_accepted": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/{tenant_id}/phone/consent`
**Summary**: Phone Consent  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `PhoneConsentRequest`
```json
{
  "phone_number": "string",
  "sms_consent": false,
  "disclosure_hash": "string"
}
```

**Response 201**: `PhoneConsentResponse`
```json
{
  "user_endpoint_id": "string",
  "verification_status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/{tenant_id}/phone/consent/test`
**Summary**: Phone Consent Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `PhoneConsentRequest`
```json
{
  "phone_number": "string",
  "sms_consent": false,
  "disclosure_hash": "string"
}
```

**Response 201**: `PhoneConsentResponse`
```json
{
  "user_endpoint_id": "string",
  "verification_status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/{tenant_id}/phone/send-optin`
**Summary**: Send Optin  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SendOptinRequest`
```json
{
  "user_endpoint_id": "string"
}
```

**Response 200**: `SendOptinResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/signup/{tenant_id}/phone/send-optin/test`
**Summary**: Send Optin Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SendOptinRequest`
```json
{
  "user_endpoint_id": "string"
}
```

**Response 200**: `SendOptinResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/signup/{tenant_id}/state`
**Summary**: Get Signup State Route  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `SignupStateResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "collected_data": {}
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/signup/{tenant_id}/state/test`
**Summary**: Get Signup State Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `SignupStateResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "collected_data": {}
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step2`
**Summary**: Advance Signup Step2  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step2/test`
**Summary**: Advance Step2 Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step3`
**Summary**: Advance Signup Step3  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step3/test`
**Summary**: Advance Step3 Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step4`
**Summary**: Advance Signup Step4  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step4/test`
**Summary**: Advance Step4 Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step5`
**Summary**: Advance Signup Step5  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/signup/{tenant_id}/step5/test`
**Summary**: Advance Step5 Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SignupStepRequest`
```json
{
  "documents_accepted": "Documents Accepted",
  "phone_number": "Phone Number",
  "sms_consent": "Sms Consent",
  "disclosure_hash": "Disclosure Hash",
  "selected_tier_id": "Selected Tier Id",
  "confirmed": "Confirmed",
  "stripe_payment_method_id": "Stripe Payment Method Id"
}
```

**Response 200**: `SignupStepResponse`
```json
{
  "tenant_id": "string",
  "signup_state": "string",
  "next_step": "Next Step"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### sites

#### `GET /api/v1/sites/`
**Summary**: List Sites  
**Auth**: Required  

**Parameters**:
- `customer_id` (query, , optional)
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Sites Api V1 Sites  Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "customer_id": "string",
    "name": "Name",
    "notes": "Notes",
    "jurisdiction_code": "Jurisdiction Code",
    "is_active": false,
    "address": "object"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/sites/`
**Summary**: Create Site  
**Auth**: Required  

**Request body**: `SiteCreate`
```json
{
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "address": "object",
  "site_type": "Site Type"
}
```

**Response 201**: `SiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "is_active": false,
  "address": "object"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/sites/test`
**Summary**: List Sites Test  

**Parameters**:
- `customer_id` (query, , optional)
- `skip` (query, integer, optional, default: 0)
- `limit` (query, integer, optional, default: 100)

**Response 200**: `Response List Sites Test Api V1 Sites Test Get`
```json
[
  {
    "id": "string",
    "tenant_id": "string",
    "customer_id": "string",
    "name": "Name",
    "notes": "Notes",
    "jurisdiction_code": "Jurisdiction Code",
    "is_active": false,
    "address": "object"
  }
]
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/sites/test`
**Summary**: Create Site Test  

**Request body**: `SiteCreate`
```json
{
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "address": "object",
  "site_type": "Site Type"
}
```

**Response 201**: `SiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "is_active": false,
  "address": "object"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/sites/{site_id}`
**Summary**: Get Site  
**Auth**: Required  

**Parameters**:
- `site_id` (path, string, required)

**Response 200**: `SiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "is_active": false,
  "address": "object"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/sites/{site_id}`
**Summary**: Update Site  
**Auth**: Required  

**Parameters**:
- `site_id` (path, string, required)

**Request body**: `SiteCreate`
```json
{
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "address": "object",
  "site_type": "Site Type"
}
```

**Response 200**: `SiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "is_active": false,
  "address": "object"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/sites/{site_id}/test`
**Summary**: Get Site Test  

**Parameters**:
- `site_id` (path, string, required)

**Response 200**: `SiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "is_active": false,
  "address": "object"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/sites/{site_id}/test`
**Summary**: Update Site Test  

**Parameters**:
- `site_id` (path, string, required)

**Request body**: `SiteCreate`
```json
{
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "address": "object",
  "site_type": "Site Type"
}
```

**Response 200**: `SiteResponse`
```json
{
  "id": "string",
  "tenant_id": "string",
  "customer_id": "string",
  "name": "Name",
  "notes": "Notes",
  "jurisdiction_code": "Jurisdiction Code",
  "is_active": false,
  "address": "object"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### sms

#### `GET /api/v1/sms/quota/`
**Summary**: Get current SMS quota for tenant  
**Auth**: Required  

**Response 200**: `SmsQuotaResponse`
```json
{
  "period_start": "Period Start",
  "period_end": "Period End",
  "included_segments": 0,
  "used_segments": 0,
  "overage_segments": 0,
  "remaining_segments": 0,
  "cap_policy": "string",
  "projected_month_end_segments": "Projected Month End Segments"
}
```

---

#### `GET /api/v1/sms/quota/test`
**Summary**: [TEST] Get SMS quota — no auth  

**Response 200**: `SmsQuotaResponse`
```json
{
  "period_start": "Period Start",
  "period_end": "Period End",
  "included_segments": 0,
  "used_segments": 0,
  "overage_segments": 0,
  "remaining_segments": 0,
  "cap_policy": "string",
  "projected_month_end_segments": "Projected Month End Segments"
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/assign-number`
**Summary**: Assign selected phone number to campaign  
**Auth**: Required  

**Request body**: `AssignNumberRequest`
```json
{
  "phone_number": "string"
}
```

**Response 200**: `AssignNumberResponse`
```json
{
  "status": "string",
  "telnyx_phone_number": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/assign-number/test`
**Summary**: [TEST] Assign phone number — no auth  

**Request body**: `AssignNumberRequest`
```json
{
  "phone_number": "string"
}
```

**Response 200**: `AssignNumberResponse`
```json
{
  "status": "string",
  "telnyx_phone_number": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/available-numbers`
**Summary**: Get available phone numbers for an area code  
**Auth**: Required  

**Parameters**:
- `area_code` (query, string, required) — 3-digit US area code
- `limit` (query, integer, optional, default: 10)

**Response 200**: `AvailableNumbersResponse`
```json
{
  "numbers": [
    {
      "phone_number": "...",
      "locality": "...",
      "region": "...",
      "monthly_cost_millicents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/available-numbers/test`
**Summary**: [TEST] Get available phone numbers — no auth  

**Parameters**:
- `area_code` (query, string, required) — 3-digit US area code
- `limit` (query, integer, optional, default: 10)

**Response 200**: `AvailableNumbersResponse`
```json
{
  "numbers": [
    {
      "phone_number": "...",
      "locality": "...",
      "region": "...",
      "monthly_cost_millicents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/checkout`
**Summary**: Create Stripe Checkout session for 10DLC setup  
**Auth**: Required  

**Response 200**: `CheckoutResponse`
```json
{
  "checkout_url": "string",
  "checkout_session_id": "string"
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/checkout/test`
**Summary**: [TEST] Create Stripe Checkout — no auth  

**Response 200**: `CheckoutResponse`
```json
{
  "checkout_url": "string",
  "checkout_session_id": "string"
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/otp`
**Summary**: Submit sole-proprietor OTP code  
**Auth**: Required  

**Request body**: `OtpRequest`
```json
{
  "otp_code": "string"
}
```

**Response 200**: `OtpResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/otp/test`
**Summary**: [TEST] Submit sole-prop OTP — no auth  

**Request body**: `OtpRequest`
```json
{
  "otp_code": "string"
}
```

**Response 200**: `OtpResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/provision`
**Summary**: Initiate 10DLC provisioning  
**Auth**: Required  

**Request body**: `ProvisionRequest`
```json
{
  "entity_type": "string",
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein": "Ein",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State"
}
```

**Response 200**: `ProvisionResponse`
```json
{
  "registration_id": "string",
  "status": "string",
  "entity_type": "string",
  "quote": {
    "entity_type": "string",
    "setup_total_millicents": 0,
    "recurring_monthly_millicents": 0,
    "setup_items": [
      "..."
    ],
    "recurring_items": [
      "..."
    ]
  }
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/provision/test`
**Summary**: [TEST] Initiate 10DLC provisioning — no auth  

**Request body**: `ProvisionRequest`
```json
{
  "entity_type": "string",
  "legal_business_name": "string",
  "dba_name": "Dba Name",
  "ein": "Ein",
  "hq_address_line1": "Hq Address Line1",
  "hq_address_line2": "Hq Address Line2",
  "hq_city": "Hq City",
  "hq_state": "Hq State"
}
```

**Response 200**: `ProvisionResponse`
```json
{
  "registration_id": "string",
  "status": "string",
  "entity_type": "string",
  "quote": {
    "entity_type": "string",
    "setup_total_millicents": 0,
    "recurring_monthly_millicents": 0,
    "setup_items": [
      "..."
    ],
    "recurring_items": [
      "..."
    ]
  }
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/quote`
**Summary**: Get 10DLC carrier cost quote  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `CarrierQuoteResponse`
```json
{
  "entity_type": "string",
  "setup_total_millicents": 0,
  "recurring_monthly_millicents": 0,
  "setup_items": [
    {
      "fee_code": "...",
      "description": "...",
      "amount_millicents": "..."
    }
  ],
  "recurring_items": [
    {
      "fee_code": "...",
      "description": "...",
      "amount_millicents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/quote/test`
**Summary**: [TEST] Get carrier quote — no auth  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `CarrierQuoteResponse`
```json
{
  "entity_type": "string",
  "setup_total_millicents": 0,
  "recurring_monthly_millicents": 0,
  "setup_items": [
    {
      "fee_code": "...",
      "description": "...",
      "amount_millicents": "..."
    }
  ],
  "recurring_items": [
    {
      "fee_code": "...",
      "description": "...",
      "amount_millicents": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/retry`
**Summary**: Retry provisioning from payment_failed  
**Auth**: Required  

**Response 200**: `RetryResponse`
```json
{
  "status": "string",
  "quote": {
    "entity_type": "string",
    "setup_total_millicents": 0,
    "recurring_monthly_millicents": 0,
    "setup_items": [
      "..."
    ],
    "recurring_items": [
      "..."
    ]
  }
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/messaging/retry/test`
**Summary**: [TEST] Retry from payment_failed — no auth  

**Response 200**: `RetryResponse`
```json
{
  "status": "string",
  "quote": {
    "entity_type": "string",
    "setup_total_millicents": 0,
    "recurring_monthly_millicents": 0,
    "setup_items": [
      "..."
    ],
    "recurring_items": [
      "..."
    ]
  }
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/status`
**Summary**: Get 10DLC provisioning status  
**Auth**: Required  

**Response 200**: `ProvisioningStatusResponse`
```json
{
  "registration_id": "string",
  "status": "string",
  "entity_type": "string",
  "telnyx_brand_id": "Telnyx Brand Id",
  "telnyx_campaign_id": "Telnyx Campaign Id",
  "telnyx_phone_number": "Telnyx Phone Number",
  "quoted_setup_cents": "Quoted Setup Cents",
  "quoted_monthly_cents": "Quoted Monthly Cents"
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/status/test`
**Summary**: [TEST] Get provisioning status — no auth  

**Response 200**: `ProvisioningStatusResponse`
```json
{
  "registration_id": "string",
  "status": "string",
  "entity_type": "string",
  "telnyx_brand_id": "Telnyx Brand Id",
  "telnyx_campaign_id": "Telnyx Campaign Id",
  "telnyx_phone_number": "Telnyx Phone Number",
  "quoted_setup_cents": "Quoted Setup Cents",
  "quoted_monthly_cents": "Quoted Monthly Cents"
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/verticals`
**Summary**: Get carrier business verticals  
**Auth**: Required  

**Response 200**: `VerticalsResponse`
```json
{
  "verticals": [
    "string"
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/messaging/verticals/test`
**Summary**: [TEST] Get carrier verticals — no auth  

**Response 200**: `VerticalsResponse`
```json
{
  "verticals": [
    "string"
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/phone-numbers/`
**Summary**: List all phone numbers for this tenant  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `TenantPhoneNumberListResponse`
```json
{
  "numbers": [
    {
      "phone_number_id": "...",
      "phone_number": "...",
      "area_code": "...",
      "carrier": "...",
      "status": "...",
      "monthly_fee_cents": "...",
      "provisioned_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/phone-numbers/provision`
**Summary**: Provision a Telnyx phone number for this tenant  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ProvisionNumberRequest`
```json
{
  "area_code": "Area Code"
}
```

**Response 200**: `TenantPhoneNumberResponse`
```json
{
  "phone_number_id": "string",
  "phone_number": "string",
  "area_code": "string",
  "carrier": "string",
  "status": "string",
  "monthly_fee_cents": 0,
  "provisioned_at": "Provisioned At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/phone-numbers/test`
**Summary**: [TEST] List phone numbers — no auth  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `TenantPhoneNumberListResponse`
```json
{
  "numbers": [
    {
      "phone_number_id": "...",
      "phone_number": "...",
      "area_code": "...",
      "carrier": "...",
      "status": "...",
      "monthly_fee_cents": "...",
      "provisioned_at": "..."
    }
  ]
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/phone-numbers/test/provision`
**Summary**: [TEST] Provision phone number — no auth  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ProvisionNumberRequest`
```json
{
  "area_code": "Area Code"
}
```

**Response 200**: `TenantPhoneNumberResponse`
```json
{
  "phone_number_id": "string",
  "phone_number": "string",
  "area_code": "string",
  "carrier": "string",
  "status": "string",
  "monthly_fee_cents": 0,
  "provisioned_at": "Provisioned At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### subscription

#### `GET /api/v1/subscription-tiers/`
**Summary**: List Subscription Tiers  
**Auth**: Required  

**Response 200**: `SubscriptionTiersListResponse`
```json
{
  "tiers": [
    {
      "tier_id": "...",
      "tier_name": "...",
      "display_label": "...",
      "monthly_price_cents": "...",
      "annual_price_cents": "...",
      "is_trial": "...",
      "trial_duration_days": "...",
      "schedule_lanes": "..."
    }
  ]
}
```

---

#### `GET /api/v1/subscription-tiers/test`
**Summary**: List Subscription Tiers Test  

**Response 200**: `SubscriptionTiersListResponse`
```json
{
  "tiers": [
    {
      "tier_id": "...",
      "tier_name": "...",
      "display_label": "...",
      "monthly_price_cents": "...",
      "annual_price_cents": "...",
      "is_trial": "...",
      "trial_duration_days": "...",
      "schedule_lanes": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/subscription`
**Summary**: Get Tenant Subscription  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `TenantSubscriptionResponse`
```json
{
  "current_tier": {
    "tier_id": "string",
    "tier_name": "string",
    "display_label": "string",
    "monthly_price_cents": 0,
    "annual_price_cents": 0,
    "is_trial": false,
    "trial_duration_days": "Trial Duration Days",
    "schedule_lanes": 0
  },
  "trial_ends_at": "Trial Ends At",
  "stripe_customer_id": "Stripe Customer Id",
  "usage": "object",
  "tier_override": "object",
  "plan_summary": {
    "status_code": "Status Code",
    "status_name": "Status Name",
    "is_billing_active": false,
    "billing_interval": "Billing Interval",
    "renews_at": "Renews At",
    "free_period_ends_at": "Free Period Ends At"
  },
  "charter_eligible": false,
  "limits": {
    "outbound_sms_segments": "Outbound Sms Segments",
    "schedule_lanes": "Schedule Lanes",
    "voice_ai_minutes": "Voice Ai Minutes"
  }
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/change-tier`
**Summary**: Change Tier  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ChangeTierRequest`
```json
{
  "target_tier_id": "string",
  "billing_interval": "string"
}
```

**Response 202**: `ChangeTierResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/change-tier/test`
**Summary**: Change Tier Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ChangeTierRequest`
```json
{
  "target_tier_id": "string",
  "billing_interval": "string"
}
```

**Response 202**: `ChangeTierResponse`
```json
{
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial`
**Summary**: Convert From Trial  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ConvertFromTrialRequest`
```json
{
  "target_tier_id": "string",
  "payment_method_id": "string",
  "billing_email": "string",
  "billing_interval": "string"
}
```

**Response 202**: `ConvertFromTrialResponse`
```json
{
  "psp_subscription_id": "string",
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial/test`
**Summary**: Convert From Trial Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ConvertFromTrialRequest`
```json
{
  "target_tier_id": "string",
  "payment_method_id": "string",
  "billing_email": "string",
  "billing_interval": "string"
}
```

**Response 202**: `ConvertFromTrialResponse`
```json
{
  "psp_subscription_id": "string",
  "status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/resume`
**Summary**: Resume Subscription  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ResumeSubscriptionRequest`
```json
{
  "stripe_payment_method_id": "string"
}
```

**Response 200**: `ResumeSubscriptionResponse`
```json
{
  "psp_subscription_id": "string",
  "status": "string",
  "billing_cycle_anchor": "Billing Cycle Anchor"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/resume/test`
**Summary**: Resume Subscription Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `ResumeSubscriptionRequest`
```json
{
  "stripe_payment_method_id": "string"
}
```

**Response 200**: `ResumeSubscriptionResponse`
```json
{
  "psp_subscription_id": "string",
  "status": "string",
  "billing_cycle_anchor": "Billing Cycle Anchor"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/tenants/{tenant_id}/subscription/test`
**Summary**: Get Tenant Subscription Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Response 200**: `TenantSubscriptionResponse`
```json
{
  "current_tier": {
    "tier_id": "string",
    "tier_name": "string",
    "display_label": "string",
    "monthly_price_cents": 0,
    "annual_price_cents": 0,
    "is_trial": false,
    "trial_duration_days": "Trial Duration Days",
    "schedule_lanes": 0
  },
  "trial_ends_at": "Trial Ends At",
  "stripe_customer_id": "Stripe Customer Id",
  "usage": "object",
  "tier_override": "object",
  "plan_summary": {
    "status_code": "Status Code",
    "status_name": "Status Name",
    "is_billing_active": false,
    "billing_interval": "Billing Interval",
    "renews_at": "Renews At",
    "free_period_ends_at": "Free Period Ends At"
  },
  "charter_eligible": false,
  "limits": {
    "outbound_sms_segments": "Outbound Sms Segments",
    "schedule_lanes": "Schedule Lanes",
    "voice_ai_minutes": "Voice Ai Minutes"
  }
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade`
**Summary**: Upgrade Tenant Subscription  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SubscriptionUpgradeRequest`
```json
{
  "target_tier_id": "string"
}
```

**Response 200**: `SubscriptionUpgradeResponse`
```json
{
  "redirect_to_stripe": false,
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter`
**Summary**: Upgrade From Charter  
**Auth**: Required  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `UpgradeFromCharterRequest`
```json
{
  "billing_interval": "string"
}
```

**Response 200**: `UpgradeFromCharterResponse`
```json
{
  "psp_subscription_id": "string",
  "new_tier_name": "string",
  "billing_interval": "string",
  "charter_eligible_forfeited": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter/test`
**Summary**: Upgrade From Charter Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `UpgradeFromCharterRequest`
```json
{
  "billing_interval": "string"
}
```

**Response 200**: `UpgradeFromCharterResponse`
```json
{
  "psp_subscription_id": "string",
  "new_tier_name": "string",
  "billing_interval": "string",
  "charter_eligible_forfeited": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade/test`
**Summary**: Upgrade Tenant Subscription Test  

**Parameters**:
- `tenant_id` (path, string, required)

**Request body**: `SubscriptionUpgradeRequest`
```json
{
  "target_tier_id": "string"
}
```

**Response 200**: `SubscriptionUpgradeResponse`
```json
{
  "redirect_to_stripe": false,
  "message": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### sync

#### `GET /api/v1/sync/test/{surface}/status`
**Summary**: [TEST] Sync status — no auth required  

**Parameters**:
- `surface` (path, string, required)

**Response 200**: `SyncStatusResponse`
```json
{
  "surface": "string",
  "state": "string",
  "pending_count": 0,
  "pending_items": [
    {
      "type": "...",
      "label": "..."
    }
  ],
  "last_sync_at": "Last Sync At",
  "next_sync_at": "Next Sync At",
  "manual_trigger_supported": false,
  "resolve_target": "Resolve Target"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/sync/{surface}/status`
**Summary**: Unified sync-surface status  
**Auth**: Required  

**Parameters**:
- `surface` (path, string, required)

**Response 200**: `SyncStatusResponse`
```json
{
  "surface": "string",
  "state": "string",
  "pending_count": 0,
  "pending_items": [
    {
      "type": "...",
      "label": "..."
    }
  ],
  "last_sync_at": "Last Sync At",
  "next_sync_at": "Next Sync At",
  "manual_trigger_supported": false,
  "resolve_target": "Resolve Target"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### team-invites

#### `GET /api/v1/invites/{token}`
**Summary**: Get Public Invite  

**Parameters**:
- `token` (path, string, required)

**Response 200**: `TeamInvitePublicResponse`
```json
{
  "tenant_name": "string",
  "email": "string",
  "role_code": "Role Code",
  "expires_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/invites`
**Summary**: List Invites  
**Auth**: Required  

**Response 200**: `Response List Invites Api V1 Users Invites Get`
```json
[
  {
    "id": "string",
    "email": "string",
    "role_code": "Role Code",
    "invited_by": "Invited By",
    "created_at": "string",
    "expires_at": "string",
    "accepted_at": "Accepted At",
    "is_active": false
  }
]
```

---

#### `POST /api/v1/users/invites`
**Summary**: Create Invite  
**Auth**: Required  

**Parameters**:
- `Idempotency-Key` (header, , optional)

**Request body**: `TeamInviteCreateRequest`
```json
{
  "email": "string",
  "role_code": "string"
}
```

**Response 201**: `TeamInviteResponse`
```json
{
  "id": "string",
  "email": "string",
  "role_code": "Role Code",
  "expires_at": "string",
  "created_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/invites/test`
**Summary**: List Invites Test  

**Response 200**: `Response List Invites Test Api V1 Users Invites Test Get`
```json
[
  {
    "id": "string",
    "email": "string",
    "role_code": "Role Code",
    "invited_by": "Invited By",
    "created_at": "string",
    "expires_at": "string",
    "accepted_at": "Accepted At",
    "is_active": false
  }
]
```

---

#### `POST /api/v1/users/invites/test`
**Summary**: Create Invite Test  

**Parameters**:
- `Idempotency-Key` (header, , optional)

**Request body**: `TeamInviteCreateRequest`
```json
{
  "email": "string",
  "role_code": "string"
}
```

**Response 201**: `TeamInviteResponse`
```json
{
  "id": "string",
  "email": "string",
  "role_code": "Role Code",
  "expires_at": "string",
  "created_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/invites/{invite_id}/resend`
**Summary**: Resend Invite  
**Auth**: Required  

**Parameters**:
- `invite_id` (path, string, required)
- `Idempotency-Key` (header, , optional)

**Response 200**: `TeamInviteResendResponse`
```json
{
  "id": "string",
  "email": "string",
  "expires_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/invites/{invite_id}/resend/test`
**Summary**: Resend Invite Test  

**Parameters**:
- `invite_id` (path, string, required)
- `Idempotency-Key` (header, , optional)

**Response 200**: `TeamInviteResendResponse`
```json
{
  "id": "string",
  "email": "string",
  "expires_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/invites/{invite_id}/revoke`
**Summary**: Revoke Invite  
**Auth**: Required  

**Parameters**:
- `invite_id` (path, string, required)
- `Idempotency-Key` (header, , optional)

**Response 200**: `TeamInviteRevokeResponse`
```json
{
  "id": "string",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/users/invites/{invite_id}/revoke/test`
**Summary**: Revoke Invite Test  

**Parameters**:
- `invite_id` (path, string, required)
- `Idempotency-Key` (header, , optional)

**Response 200**: `TeamInviteRevokeResponse`
```json
{
  "id": "string",
  "is_active": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### untagged

#### `GET /`
**Summary**: Root  

**Response 200**: Successful Response

---

#### `GET /api/v1/hello`
**Summary**: Hello Aeveofab  

**Response 200**: Successful Response

---

### users

#### `DELETE /api/v1/users/me/avatar`
**Summary**: Delete Avatar  
**Auth**: Required  

**Response 200**: `AvatarDeleteResponse`
```json
{
  "success": false
}
```

---

#### `POST /api/v1/users/me/avatar/presigned-url`
**Summary**: Get Avatar Presigned Url  
**Auth**: Required  

**Response 201**: `AvatarPresignedUrlResponse`
```json
{
  "upload_url": "string",
  "s3_key": "string"
}
```

---

#### `POST /api/v1/users/me/avatar/presigned-url/test`
**Summary**: Get Avatar Presigned Url Test  

**Response 201**: `AvatarPresignedUrlResponse`
```json
{
  "upload_url": "string",
  "s3_key": "string"
}
```

---

#### `DELETE /api/v1/users/me/avatar/test`
**Summary**: Delete Avatar Test  

**Response 200**: `AvatarDeleteResponse`
```json
{
  "success": false
}
```

---

#### `GET /api/v1/users/me/preferences`
**Summary**: Get Preferences  
**Auth**: Required  

**Response 200**: `UserPreferenceResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "preferences": {},
  "updated_at": "string"
}
```

---

#### `PATCH /api/v1/users/me/preferences`
**Summary**: Update Preferences  
**Auth**: Required  

**Request body**: `UserPreferencePatch`
```json
{
  "field_mode_enabled": "Field Mode Enabled"
}
```

**Response 200**: `UserPreferenceResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "preferences": {},
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/me/preferences/test`
**Summary**: Get Preferences Test  

**Response 200**: `UserPreferenceResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "preferences": {},
  "updated_at": "string"
}
```

---

#### `PATCH /api/v1/users/me/preferences/test`
**Summary**: Update Preferences Test  

**Request body**: `UserPreferencePatch`
```json
{
  "field_mode_enabled": "Field Mode Enabled"
}
```

**Response 200**: `UserPreferenceResponse`
```json
{
  "user_id": "string",
  "tenant_id": "string",
  "preferences": {},
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/me/profile`
**Summary**: Get Profile  
**Auth**: Required  

**Response 200**: `UserProfileResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "string",
  "phone_number": "Phone Number",
  "time_zone": "Time Zone",
  "profile_photo_s3_key": "Profile Photo S3 Key",
  "profile_photo_url": "Profile Photo Url"
}
```

---

#### `PATCH /api/v1/users/me/profile`
**Summary**: Update Profile  
**Auth**: Required  

**Request body**: `UserProfilePatchRequest`
```json
{
  "first_name": "First Name",
  "last_name": "Last Name",
  "phone_number": "Phone Number",
  "time_zone": "Time Zone",
  "profile_photo_s3_key": "Profile Photo S3 Key"
}
```

**Response 200**: `UserProfileResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "string",
  "phone_number": "Phone Number",
  "time_zone": "Time Zone",
  "profile_photo_s3_key": "Profile Photo S3 Key",
  "profile_photo_url": "Profile Photo Url"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/users/me/profile/test`
**Summary**: Get Profile Test  

**Response 200**: `UserProfileResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "string",
  "phone_number": "Phone Number",
  "time_zone": "Time Zone",
  "profile_photo_s3_key": "Profile Photo S3 Key",
  "profile_photo_url": "Profile Photo Url"
}
```

---

#### `PATCH /api/v1/users/me/profile/test`
**Summary**: Update Profile Test  

**Request body**: `UserProfilePatchRequest`
```json
{
  "first_name": "First Name",
  "last_name": "Last Name",
  "phone_number": "Phone Number",
  "time_zone": "Time Zone",
  "profile_photo_s3_key": "Profile Photo S3 Key"
}
```

**Response 200**: `UserProfileResponse`
```json
{
  "id": "string",
  "first_name": "First Name",
  "last_name": "Last Name",
  "email": "string",
  "phone_number": "Phone Number",
  "time_zone": "Time Zone",
  "profile_photo_s3_key": "Profile Photo S3 Key",
  "profile_photo_url": "Profile Photo Url"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/users/test/{user_id}/color`
**Summary**: [TEST] Set user display color — no auth required  

**Parameters**:
- `user_id` (path, string, required)

**Request body**: `UserColorPatch`
```json
{
  "display_color": "string"
}
```

**Response 200**: `UserColorResponse`
```json
{
  "user_id": "string",
  "display_color": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `PATCH /api/v1/users/{user_id}/color`
**Summary**: Set user display color for dispatch board  
**Auth**: Required  

**Parameters**:
- `user_id` (path, string, required)

**Request body**: `UserColorPatch`
```json
{
  "display_color": "string"
}
```

**Response 200**: `UserColorResponse`
```json
{
  "user_id": "string",
  "display_color": "string",
  "updated_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### voice

#### `POST /api/v1/voice/command`
**Summary**: Process Voice Command  
**Auth**: Required  

**Response 200**: `VoiceCommandResponse`
```json
{
  "transcribed_text": "string",
  "parsed_intent": {},
  "session_id": "string",
  "action_result": "Action Result"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/command/test`
**Summary**: Process Voice Command Test  

**Response 200**: `VoiceCommandResponse`
```json
{
  "transcribed_text": "string",
  "parsed_intent": {},
  "session_id": "string",
  "action_result": "Action Result"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/command/{idempotency_uuid}`
**Summary**: Poll offline voice command processing status  
**Auth**: Required  

**Parameters**:
- `idempotency_uuid` (path, string, required)

**Response 200**: `VoiceCommandStatusResponse`
```json
{
  "voice_command_log_id": 0,
  "processing_status": "Processing Status",
  "intent_detected": "Intent Detected",
  "action_executed": "Action Executed",
  "pending_confirmation": false,
  "captured_at": "Captured At",
  "transcribed_at": "Transcribed At",
  "parsed_at": "Parsed At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/command/{idempotency_uuid}/test`
**Summary**: [TEST] Poll voice command status (no JWT)  

**Parameters**:
- `idempotency_uuid` (path, string, required)

**Response 200**: `VoiceCommandStatusResponse`
```json
{
  "voice_command_log_id": 0,
  "processing_status": "Processing Status",
  "intent_detected": "Intent Detected",
  "action_executed": "Action Executed",
  "pending_confirmation": false,
  "captured_at": "Captured At",
  "transcribed_at": "Transcribed At",
  "parsed_at": "Parsed At"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/feedback`
**Summary**: List Feedback  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `cursor` (query, , optional)
- `exported` (query, , optional)

**Response 200**: `FeedbackListResponse`
```json
{
  "feedback_items": [
    {
      "feedback_id": "...",
      "voice_command_log_id": "...",
      "original_transcription": "...",
      "corrected_text": "...",
      "intent_misparsed": "...",
      "corrected_intent": "...",
      "feedback_notes": "...",
      "exported_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/feedback`
**Summary**: Submit Feedback  
**Auth**: Required  

**Request body**: `VoiceFeedbackCreate`
```json
{
  "voice_command_log_id": "Voice Command Log Id",
  "original_transcription": "string",
  "corrected_text": "Corrected Text",
  "intent_misparsed": false,
  "corrected_intent": "Corrected Intent",
  "feedback_notes": "Feedback Notes"
}
```

**Response 201**: `VoiceFeedbackCreatedResponse`
```json
{
  "feedback_id": "string",
  "tenant_id": "string",
  "created_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/feedback/test`
**Summary**: List Feedback Test  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `cursor` (query, , optional)
- `exported` (query, , optional)

**Response 200**: `FeedbackListResponse`
```json
{
  "feedback_items": [
    {
      "feedback_id": "...",
      "voice_command_log_id": "...",
      "original_transcription": "...",
      "corrected_text": "...",
      "intent_misparsed": "...",
      "corrected_intent": "...",
      "feedback_notes": "...",
      "exported_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/feedback/test`
**Summary**: Submit Feedback Test  

**Request body**: `VoiceFeedbackCreate`
```json
{
  "voice_command_log_id": "Voice Command Log Id",
  "original_transcription": "string",
  "corrected_text": "Corrected Text",
  "intent_misparsed": false,
  "corrected_intent": "Corrected Intent",
  "feedback_notes": "Feedback Notes"
}
```

**Response 201**: `VoiceFeedbackCreatedResponse`
```json
{
  "feedback_id": "string",
  "tenant_id": "string",
  "created_at": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/sessions/`
**Summary**: List Sessions  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `cursor` (query, , optional)

**Response 200**: `SessionListResponse`
```json
{
  "sessions": [
    {
      "session_id": "...",
      "session_number": "...",
      "title": "...",
      "title_auto_generated": "...",
      "status": "...",
      "created_at": "...",
      "updated_at": "...",
      "archived_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/sessions/`
**Summary**: Create Voice Session — FE-B23/A3  
**Auth**: Required  

**Response 201**: `SessionResponse`
```json
{
  "session_id": "string",
  "session_number": 0,
  "title": "Title",
  "title_auto_generated": false,
  "status": "string",
  "created_at": "string",
  "updated_at": "string",
  "archived_at": "Archived At"
}
```

---

#### `GET /api/v1/voice/sessions/test`
**Summary**: List Sessions Test  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `cursor` (query, , optional)

**Response 200**: `SessionListResponse`
```json
{
  "sessions": [
    {
      "session_id": "...",
      "session_number": "...",
      "title": "...",
      "title_auto_generated": "...",
      "status": "...",
      "created_at": "...",
      "updated_at": "...",
      "archived_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/sessions/test`
**Summary**: Create Voice Session (TEST — no auth)  

**Response 201**: `SessionResponse`
```json
{
  "session_id": "string",
  "session_number": 0,
  "title": "Title",
  "title_auto_generated": false,
  "status": "string",
  "created_at": "string",
  "updated_at": "string",
  "archived_at": "Archived At"
}
```

---

#### `GET /api/v1/voice/sessions/test/{session_id}/messages`
**Summary**: Get Session Messages Test  

**Parameters**:
- `session_id` (path, string, required)
- `limit` (query, integer, optional, default: 50)
- `cursor` (query, , optional)

**Response 200**: `SessionMessagesResponse`
```json
{
  "messages": [
    {
      "message_id": "...",
      "session_id": "...",
      "role": "...",
      "content_text": "...",
      "structured_content_json": "...",
      "created_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/sessions/{session_id}/messages`
**Summary**: Get Session Messages  
**Auth**: Required  

**Parameters**:
- `session_id` (path, string, required)
- `limit` (query, integer, optional, default: 50)
- `cursor` (query, , optional)

**Response 200**: `SessionMessagesResponse`
```json
{
  "messages": [
    {
      "message_id": "...",
      "session_id": "...",
      "role": "...",
      "content_text": "...",
      "structured_content_json": "...",
      "created_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/transcripts`
**Summary**: List Transcripts  
**Auth**: Required  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `cursor` (query, , optional)
- `intent` (query, , optional)

**Response 200**: `TranscriptListResponse`
```json
{
  "transcripts": [
    {
      "voice_command_log_id": "...",
      "tenant_id": "...",
      "user_id": "...",
      "original_transcription": "...",
      "intent_detected": "...",
      "is_successful": "...",
      "whisper_latency_ms": "...",
      "created_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `GET /api/v1/voice/transcripts/test`
**Summary**: List Transcripts Test  

**Parameters**:
- `limit` (query, integer, optional, default: 20)
- `cursor` (query, , optional)
- `intent` (query, , optional)

**Response 200**: `TranscriptListResponse`
```json
{
  "transcripts": [
    {
      "voice_command_log_id": "...",
      "tenant_id": "...",
      "user_id": "...",
      "original_transcription": "...",
      "intent_detected": "...",
      "is_successful": "...",
      "whisper_latency_ms": "...",
      "created_at": "..."
    }
  ],
  "next_cursor": "Next Cursor",
  "has_more": false
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/upload-audio`
**Summary**: Upload offline-captured audio for async processing  
**Auth**: Required  

**Response 202**: `VoiceUploadResponse`
```json
{
  "voice_command_log_id": 0,
  "idempotency_uuid": "string",
  "processing_status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

#### `POST /api/v1/voice/upload-audio/test`
**Summary**: [TEST] Upload offline audio (no JWT)  

**Response 202**: `VoiceUploadResponse`
```json
{
  "voice_command_log_id": 0,
  "idempotency_uuid": "string",
  "processing_status": "string"
}
```

**Response 422**: `HTTPValidationError`
```json
{
  "detail": [
    {
      "loc": "...",
      "msg": "...",
      "type": "...",
      "input": "...",
      "ctx": "..."
    }
  ]
}
```

---

### webhooks

#### `POST /api/v1/webhooks/quickbooks`
**Summary**: Quickbooks Webhook  

**Response 200**: Successful Response

---

#### `POST /api/v1/webhooks/sms/telnyx-inbound`
**Summary**: Telnyx inbound SMS webhook receiver  

**Response 200**: Successful Response

---

#### `POST /api/v1/webhooks/stripe`
**Summary**: Stripe Webhook Handler  

**Response 200**: Successful Response

---

#### `POST /api/v1/webhooks/stripe-connect`
**Summary**: Stripe Connect Webhook Handler  

**Response 200**: Successful Response

---
