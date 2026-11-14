--- SAMPLE CREATE TABLE STATEMENT ---
CREATE TABLE audit.event (
    id bigint NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    tenant_id uuid,
    user_id uuid,
    actor_type character varying NOT NULL,
    user_role character varying,
    ip inet,
    user_agent character varying,
    request_id character varying,
    correlation_id character varying,
    idempotency_key character varying,
    entity_name character varying NOT NULL,
    entity_id character varying NOT NULL,
    action character varying NOT NULL,
    old_values jsonb,
    new_values jsonb,
    reason character varying,
    contextdata jsonb,
    prev_hash character varying,
    self_hash character varying,
    hashed_at timestamp with time zone,
    CONSTRAINT audit_event_actor_type_chk CHECK (((actor_type)::text = ANY ((ARRAY['system'::character varying, 'user'::character varying, 'platform'::character varying, 'external_webhook'::character varying])::text[])))
);

--- SAMPLE ALTER TABLE STATEMENT ---
ALTER TABLE ONLY audit.event ALTER COLUMN id SET DEFAULT nextval('audit.event_id_seq'::regclass);
