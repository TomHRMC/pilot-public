--
-- PostgreSQL database dump
--

\restrict hC4c34mPb0LbSDb8V5xydOtfnk52BHSLfsIPoccNrrvvriaoX809hg167LAgRDx

-- Dumped from database version 17.9 (Debian 17.9-1.pgdg12+1)
-- Dumped by pg_dump version 17.10 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA audit;


--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


--
-- Name: citext; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;


--
-- Name: EXTENSION citext; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION citext IS 'data type for case-insensitive character strings';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: log_changes(); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.log_changes() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
        DECLARE
            v_user_id    uuid;
            v_actor_type text;
            v_tenant_id  uuid;
            v_entity_id  text;
        BEGIN
            v_user_id := COALESCE(
                NULLIF(current_setting('app.user_id', true), '')::uuid,
                '00000000-0000-0000-0000-000000000000'::uuid
            );

            IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                v_actor_type := 'system';
            ELSE
                v_actor_type := 'user';
            END IF;

            BEGIN
                v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
            EXCEPTION
                WHEN undefined_column THEN v_tenant_id := NULL;
            END;

            -- FIND-169: simplified fallback chain.
            -- UUID PKs are now 'id'; string PKs on lookup tables are 'code'.
            -- Removed article_id/session_id fallbacks (both renamed by FIND-169).
            -- Kept message_id/chunk_id/corpus_id/submission_id for other tables.
            BEGIN
                v_entity_id := COALESCE(NEW.id, OLD.id)::text;
            EXCEPTION WHEN undefined_column THEN
                BEGIN
                    v_entity_id := COALESCE(NEW.code, OLD.code)::text;
                EXCEPTION WHEN undefined_column THEN
                    BEGIN
                        v_entity_id := COALESCE(NEW.tenant_id, OLD.tenant_id)::text;
                    EXCEPTION WHEN undefined_column THEN
                        BEGIN
                            v_entity_id := COALESCE(NEW.corpus_id, OLD.corpus_id)::text;
                        EXCEPTION WHEN undefined_column THEN
                            BEGIN
                                v_entity_id := COALESCE(NEW.submission_id, OLD.submission_id)::text;
                            EXCEPTION WHEN undefined_column THEN
                                BEGIN
                                    v_entity_id := COALESCE(NEW.message_id, OLD.message_id)::text;
                                EXCEPTION WHEN undefined_column THEN
                                    BEGIN
                                        v_entity_id := COALESCE(NEW.chunk_id, OLD.chunk_id)::text;
                                    EXCEPTION WHEN undefined_column THEN
                                        v_entity_id := 'unknown_' || TG_TABLE_NAME;
                                    END;
                                END;
                            END;
                        END;
                    END;
                END;
            END;

            INSERT INTO audit.event (
                tenant_id, user_id, actor_type, entity_name, entity_id, action,
                old_values, new_values, occurred_at
            ) VALUES (
                v_tenant_id, v_user_id, v_actor_type, TG_TABLE_NAME::text, v_entity_id, TG_OP,
                CASE WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb ELSE NULL END,
                CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb ELSE NULL END,
                NOW()
            );

            RETURN COALESCE(NEW, OLD);
        END;
        $$;


--
-- Name: log_changes_code_pk(); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.log_changes_code_pk() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_user_id uuid;
            v_actor_type text;
            v_tenant_id uuid;
        BEGIN
            -- Read user_id from session variable (set by application)
            -- Falls back to system UUID if not set (background jobs, migrations)
            v_user_id := COALESCE(
                NULLIF(current_setting('app.user_id', true), '')::uuid,
                '00000000-0000-0000-0000-000000000000'::uuid
            );
            
            -- Determine actor_type based on user_id
            IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                v_actor_type := 'system';
            ELSE
                v_actor_type := 'user';
            END IF;
            
            -- Safely extract tenant_id (handles tables without tenant_id column)
            BEGIN
                v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
            EXCEPTION
                WHEN undefined_column THEN
                    v_tenant_id := NULL;
            END;
            
            -- Insert audit event record capturing the change
            INSERT INTO audit.event (
                tenant_id,
                user_id,
                actor_type,
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                occurred_at
            ) VALUES (
                -- Tenant ID (NULL for platform-level tables)
                v_tenant_id,
                
                -- User ID from session variable or system UUID
                v_user_id,
                
                -- Actor type: 'user' or 'system'
                v_actor_type,
                
                -- Use table name as entity type
                TG_TABLE_NAME::text,
                
                -- Extract entity ID from 'code' column (primary key for these tables)
                COALESCE(NEW.code, OLD.code)::text,
                
                -- Operation type: INSERT, UPDATE, DELETE
                TG_OP,
                
                -- Old values (for UPDATE and DELETE operations)
                CASE
                    WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb
                    ELSE NULL
                END,
                
                -- New values (for INSERT and UPDATE operations)
                CASE
                    WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb
                    ELSE NULL
                END,
                
                -- Timestamp of the change
                NOW()
            );
            
            -- Return the appropriate record to allow the operation to complete
            RETURN COALESCE(NEW, OLD);
        END;
        $$;


--
-- Name: cascade_soft_delete_to_change_order(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_change_order() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE change_order SET is_active = false
                WHERE job_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_change_order_line(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_change_order_line() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE change_order_line SET is_active = false
                WHERE change_order_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_contact(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_contact() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE contact SET is_active = false
                WHERE customer_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_invoice_line(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_invoice_line() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE invoice_line SET is_active = false
                WHERE invoice_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_invoice_line_tax_component(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_invoice_line_tax_component() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE invoice_line_tax_component SET is_active = false
                WHERE invoice_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_job_expense(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_job_expense() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE job_expense SET is_active = false
                WHERE job_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_quote_line(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_quote_line() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE quote_line SET is_active = false
                WHERE quote_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_quote_line_tax_component(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_quote_line_tax_component() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE quote_line_tax_component SET is_active = false
                WHERE quote_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: cascade_soft_delete_to_site(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cascade_soft_delete_to_site() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE site SET is_active = false
                WHERE customer_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: guard_created_fields_immutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.guard_created_fields_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
        DECLARE
          has_created_by boolean;
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            -- Reject attempts to change created_at
            IF NEW.created_at IS DISTINCT FROM OLD.created_at THEN
              RAISE EXCEPTION 'created_at is immutable (cannot be changed after insert)'
                USING ERRCODE = '23514',
                      HINT = 'Remove created_at from UPDATE statement';
            END IF;
            
            -- Check if table has created_by column
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns 
              WHERE table_schema = TG_TABLE_SCHEMA 
                AND table_name = TG_TABLE_NAME 
                AND column_name = 'created_by'
            ) INTO has_created_by;
            
            -- Reject attempts to change created_by (if column exists)
            IF has_created_by THEN
              -- Use dynamic SQL to check created_by value
              EXECUTE format(
                'SELECT ($1).created_by IS DISTINCT FROM ($2).created_by'
              ) USING NEW, OLD INTO has_created_by;
              
              IF has_created_by THEN
                RAISE EXCEPTION 'created_by is immutable (cannot be changed after insert)'
                  USING ERRCODE = '23514',
                        HINT = 'Remove created_by from UPDATE statement';
              END IF;
            END IF;
          END IF;
          
          RETURN NEW;
        END;
        $_$;


--
-- Name: guard_tenant_user_platform_isolation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.guard_tenant_user_platform_isolation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            is_platform bool;
        BEGIN
            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                -- Use explicit is_platform_user boolean (GENERATED column)
                SELECT is_platform_user INTO is_platform
                FROM "user"
                WHERE id = NEW.user_id;
                
                IF is_platform THEN
                    RAISE EXCEPTION 'User % is a platform user and cannot be assigned to a tenant',
                        NEW.user_id
                        USING ERRCODE = '23514',
                              HINT = 'Platform users (staff, superadmin) cannot be tenant users';
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$;


--
-- Name: guard_user_endpoint_primary_email_fn(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.guard_user_endpoint_primary_email_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
          has_other_primary boolean;
          skip_check TEXT;
        BEGIN
          IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
            IF NEW.channel = 'email' THEN
              NEW.value := lower(trim(NEW.value));
              
              -- If this endpoint is being set to primary
              IF COALESCE(NEW.is_primary, false) AND NOT COALESCE(OLD.is_primary, false) THEN
                -- Set both flags to prevent race conditions during auto-demotion
                PERFORM set_config('aevofab.skip_sync', 'true', true);
                PERFORM set_config('aevofab.skip_highlander_check', 'true', true);
                
                -- Auto-demote any existing primary emails for this user
                UPDATE user_endpoint
                   SET is_primary = false, updated_at = now()
                 WHERE user_id = NEW.user_id
                   AND channel = 'email'
                   AND is_primary = true
                   AND id <> NEW.id;
                
                -- Clear both flags
                PERFORM set_config('aevofab.skip_sync', NULL, true);
                PERFORM set_config('aevofab.skip_highlander_check', NULL, true);
              END IF;

              -- Prevent demoting the ONLY primary email manually
              IF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                -- Check if we're in auto-demotion mode (bypass check)
                skip_check := current_setting('aevofab.skip_highlander_check', true);
                IF skip_check IS NULL OR skip_check != 'true' THEN
                  SELECT EXISTS (
                    SELECT 1 FROM user_endpoint
                     WHERE user_id = NEW.user_id AND channel='email' AND is_primary = true AND id <> NEW.id
                  ) INTO has_other_primary;
                  IF NOT has_other_primary THEN
                    RAISE EXCEPTION 'Cannot demote the only primary email endpoint for this user'
                      USING ERRCODE = '23514', HINT = 'Promote a different email endpoint first.';
                  END IF;
                END IF;
              END IF;
            END IF;
            RETURN NEW;

          ELSIF TG_OP = 'DELETE' THEN
            IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
              SELECT EXISTS (
                SELECT 1 FROM user_endpoint
                 WHERE user_id = OLD.user_id AND channel='email' AND is_primary = true AND id <> OLD.id
              ) INTO has_other_primary;
              IF NOT has_other_primary THEN
                RAISE EXCEPTION 'Cannot delete the only primary email endpoint for this user'
                  USING ERRCODE = '23514', HINT = 'Promote another email endpoint first.';
              END IF;
            END IF;
            RETURN OLD;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$;


--
-- Name: recalc_change_order_totals_fn(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.recalc_change_order_totals_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
          _coid uuid;
        BEGIN
          -- Determine parent change_order id from NEW/OLD
          IF TG_OP IN ('INSERT','UPDATE') THEN
            IF TG_TABLE_NAME = 'change_order_line' THEN
              _coid := NEW.change_order_id;
            ELSIF TG_TABLE_NAME = 'change_order_line_tax_component' THEN
              SELECT col.change_order_id INTO _coid FROM change_order_line col WHERE col.id = NEW.change_order_line_id;
            END IF;
          ELSE
            -- DELETE
            IF TG_TABLE_NAME = 'change_order_line' THEN
              _coid := OLD.change_order_id;
            ELSIF TG_TABLE_NAME = 'change_order_line_tax_component' THEN
              SELECT col.change_order_id INTO _coid FROM change_order_line col WHERE col.id = OLD.change_order_line_id;
            END IF;
          END IF;

          IF _coid IS NOT NULL THEN
            UPDATE change_order co SET
              subtotal_cents = COALESCE((SELECT SUM(subtotal_cents) FROM change_order_line WHERE change_order_id = _coid AND is_active = true), 0),
              tax_cents      = COALESCE((
                                  SELECT SUM(t.amount_cents)
                                    FROM change_order_line_tax_component t
                                    JOIN change_order_line l ON l.id = t.change_order_line_id
                                   WHERE l.change_order_id = _coid AND l.is_active = true
                                ), 0),
              total_cents    = COALESCE((SELECT SUM(subtotal_cents) FROM change_order_line WHERE change_order_id = _coid AND is_active = true), 0)
                                + COALESCE((
                                    SELECT SUM(t.amount_cents)
                                      FROM change_order_line_tax_component t
                                      JOIN change_order_line l ON l.id = t.change_order_line_id
                                     WHERE l.change_order_id = _coid AND l.is_active = true
                                  ), 0),
              updated_at     = now()
            WHERE co.id = _coid;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$;


--
-- Name: recalc_invoice_totals_fn(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.recalc_invoice_totals_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
          _iid uuid;
        BEGIN
          -- Determine parent invoice id from NEW/OLD
          IF TG_OP IN ('INSERT','UPDATE') THEN
            IF TG_TABLE_NAME = 'invoice_line' THEN
              _iid := NEW.invoice_id;
            ELSIF TG_TABLE_NAME = 'invoice_line_tax_component' THEN
              SELECT il.invoice_id INTO _iid FROM invoice_line il WHERE il.id = NEW.invoice_line_id;
            END IF;
          ELSE
            -- DELETE
            IF TG_TABLE_NAME = 'invoice_line' THEN
              _iid := OLD.invoice_id;
            ELSIF TG_TABLE_NAME = 'invoice_line_tax_component' THEN
              SELECT il.invoice_id INTO _iid FROM invoice_line il WHERE il.id = OLD.invoice_line_id;
            END IF;
          END IF;

          IF _iid IS NOT NULL THEN
            UPDATE invoice i SET
              subtotal_cents = COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0),
              tax_cents      = COALESCE((
                                  SELECT SUM(t.amount_cents)
                                    FROM invoice_line_tax_component t
                                    JOIN invoice_line l ON l.id = t.invoice_line_id
                                   WHERE l.invoice_id = _iid AND l.is_active = true
                                ), 0),
              total_cents    = COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0)
                                + COALESCE((
                                    SELECT SUM(t.amount_cents)
                                      FROM invoice_line_tax_component t
                                      JOIN invoice_line l ON l.id = t.invoice_line_id
                                     WHERE l.invoice_id = _iid AND l.is_active = true
                                  ), 0),
              balance_due_cents = (
                                    COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0)
                                    + COALESCE((
                                        SELECT SUM(t.amount_cents)
                                          FROM invoice_line_tax_component t
                                          JOIN invoice_line l ON l.id = t.invoice_line_id
                                         WHERE l.invoice_id = _iid AND l.is_active = true
                                      ), 0)
                                  )
                                  - COALESCE((
                                      SELECT SUM(p.amount_cents)
                                        FROM payment p
                                        JOIN payment_status ps ON ps.id = p.status_id
                                       WHERE p.invoice_id = _iid
                                         AND ps.code = 'completed'
                                    ), 0),
              updated_at     = now()
            WHERE i.id = _iid;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$;


--
-- Name: recalc_quote_totals_fn(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.recalc_quote_totals_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
          _qid uuid;
        BEGIN
          -- Determine parent quote id from NEW/OLD
          IF TG_OP IN ('INSERT','UPDATE') THEN
            IF TG_TABLE_NAME = 'quote_line' THEN
              _qid := NEW.quote_id;
            ELSIF TG_TABLE_NAME = 'quote_line_tax_component' THEN
              SELECT ql.quote_id INTO _qid FROM quote_line ql WHERE ql.id = NEW.quote_line_id;
            END IF;
          ELSE
            -- DELETE
            IF TG_TABLE_NAME = 'quote_line' THEN
              _qid := OLD.quote_id;
            ELSIF TG_TABLE_NAME = 'quote_line_tax_component' THEN
              SELECT ql.quote_id INTO _qid FROM quote_line ql WHERE ql.id = OLD.quote_line_id;
            END IF;
          END IF;

          IF _qid IS NOT NULL THEN
            UPDATE quote q SET
              subtotal_cents = COALESCE((SELECT SUM(subtotal_cents) FROM quote_line WHERE quote_id = _qid AND is_active = true), 0),
              tax_cents      = COALESCE((
                                  SELECT SUM(t.amount_cents)
                                    FROM quote_line_tax_component t
                                    JOIN quote_line l ON l.id = t.quote_line_id
                                   WHERE l.quote_id = _qid AND l.is_active = true
                                ), 0),
              total_cents    = COALESCE((SELECT SUM(subtotal_cents) FROM quote_line WHERE quote_id = _qid AND is_active = true), 0)
                                + COALESCE((
                                    SELECT SUM(t.amount_cents)
                                      FROM quote_line_tax_component t
                                      JOIN quote_line l ON l.id = t.quote_line_id
                                     WHERE l.quote_id = _qid AND l.is_active = true
                                  ), 0),
              updated_at     = now()
            WHERE q.id = _qid;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$;


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          -- Use clock_timestamp() instead of NOW() to get actual current time
          -- NOW() returns transaction start time, which can cause updated_at to go backwards
          NEW.updated_at := clock_timestamp();
          RETURN NEW;
        END;
        $$;


--
-- Name: sync_user_email_from_endpoint_fn(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.sync_user_email_from_endpoint_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            next_primary_email TEXT;
            skip_sync TEXT;
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                -- If inserting a primary email endpoint, sync to user table
                IF NEW.channel = 'email' AND COALESCE(NEW.is_primary, false) THEN
                    UPDATE "user"
                    SET email = LOWER(NEW.value),
                        updated_at = NOW()
                    WHERE id = NEW.user_id;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'UPDATE') THEN
                -- If updating to primary email or changing primary email value
                IF NEW.channel = 'email' THEN
                    IF COALESCE(NEW.is_primary, false) AND 
                       (NOT COALESCE(OLD.is_primary, false) OR NEW.value IS DISTINCT FROM OLD.value) THEN
                        UPDATE "user"
                        SET email = LOWER(NEW.value),
                            updated_at = NOW()
                        WHERE id = NEW.user_id;
                    ELSIF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                        -- Primary was demoted - check if we should skip sync during auto-demotion
                        skip_sync := current_setting('aevofab.skip_sync', true);
                        IF skip_sync IS NULL OR skip_sync != 'true' THEN
                            -- Find next primary email
                            SELECT LOWER(value) INTO next_primary_email
                            FROM user_endpoint
                            WHERE user_id = OLD.user_id
                              AND channel = 'email'
                              AND is_primary = true
                            ORDER BY created_at DESC
                            LIMIT 1;
                            
                            UPDATE "user"
                            SET email = next_primary_email,
                                updated_at = NOW()
                            WHERE id = OLD.user_id;
                        END IF;
                        -- If skip_sync is true, do nothing - the sync will happen when new primary is promoted
                    END IF;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'DELETE') THEN
                -- If deleting primary email, find next available primary
                IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
                    SELECT LOWER(value) INTO next_primary_email
                    FROM user_endpoint
                    WHERE user_id = OLD.user_id
                      AND channel = 'email'
                      AND is_primary = true
                      AND id != OLD.id  -- Exclude the one being deleted
                    ORDER BY created_at DESC
                    LIMIT 1;
                    
                    UPDATE "user"
                    SET email = next_primary_email,
                        updated_at = NOW()
                    WHERE id = OLD.user_id;
                END IF;
                RETURN OLD;
            END IF;

            RETURN COALESCE(NEW, OLD);
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: event; Type: TABLE; Schema: audit; Owner: -
--

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


--
-- Name: event_id_seq; Type: SEQUENCE; Schema: audit; Owner: -
--

CREATE SEQUENCE audit.event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_id_seq; Type: SEQUENCE OWNED BY; Schema: audit; Owner: -
--

ALTER SEQUENCE audit.event_id_seq OWNED BY audit.event.id;


--
-- Name: address; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.address (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    line1 character varying,
    line2 character varying,
    line3 character varying,
    city character varying,
    state character varying,
    postal_code character varying,
    country character varying DEFAULT 'US'::character varying,
    latitude numeric(10,7),
    longitude numeric(10,7),
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    CONSTRAINT address_has_physical_or_gps_chk CHECK ((((line1 IS NOT NULL) AND (city IS NOT NULL)) OR ((latitude IS NOT NULL) AND (longitude IS NOT NULL))))
);


--
-- Name: address_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.address_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    tenant_id uuid,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: app_service; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_service (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    name character varying NOT NULL,
    category_code character varying NOT NULL,
    provider_code character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    external_account_id character varying
);


--
-- Name: app_service_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_service_category (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    description character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: app_service_provider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_service_provider (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    description character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: auth_api_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_api_token (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    user_id uuid,
    name character varying NOT NULL,
    token_hash character varying NOT NULL,
    scopes character varying[],
    last_used_at timestamp with time zone,
    expires_at timestamp with time zone,
    revoked_at timestamp with time zone
);


--
-- Name: auth_email_verification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_email_verification (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    user_id uuid,
    contact_id uuid,
    token_hash character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone
);


--
-- Name: auth_jwk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_jwk (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    kid character varying NOT NULL,
    alg character varying NOT NULL,
    public_jwk jsonb NOT NULL,
    issuer_url character varying,
    discovery_url character varying,
    jwk_status_id uuid NOT NULL,
    not_before timestamp with time zone,
    not_after timestamp with time zone,
    CONSTRAINT auth_jwk_alg_chk CHECK (((alg)::text = ANY ((ARRAY['RS256'::character varying, 'ES256'::character varying, 'EdDSA'::character varying])::text[])))
);


--
-- Name: auth_mfa_otp; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_mfa_otp (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    user_id uuid,
    contact_id uuid,
    channel character varying NOT NULL,
    user_endpoint_id uuid,
    destination_masked character varying,
    code_hash character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone,
    attempt_count integer DEFAULT 0 NOT NULL,
    requested_ip inet,
    CONSTRAINT auth_mfa_otp_channel_chk CHECK (((channel)::text = ANY ((ARRAY['email'::character varying, 'sms'::character varying])::text[])))
);


--
-- Name: auth_password_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_password_history (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    user_id uuid,
    contact_id uuid,
    password_hash character varying NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: auth_password_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_password_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_password_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_password_history_id_seq OWNED BY public.auth_password_history.id;


--
-- Name: auth_password_reset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_password_reset (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    user_id uuid,
    contact_id uuid,
    token_hash character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    requested_ip inet
);


--
-- Name: auth_refresh_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_refresh_token (
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    tenant_id uuid,
    jti character varying NOT NULL,
    rotated_from_jti character varying,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    revoked_reason character varying,
    ip inet,
    user_agent character varying,
    session_id uuid
);


--
-- Name: calendar_sync_conflict; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.calendar_sync_conflict (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    job_id uuid NOT NULL,
    local_snapshot jsonb NOT NULL,
    remote_snapshot jsonb NOT NULL,
    resolution text,
    resolved_by_user_id uuid,
    resolved_at timestamp with time zone,
    conflict_type text NOT NULL,
    base_snapshot jsonb,
    pilot_modified_by_user_id uuid,
    pilot_modified_at timestamp with time zone NOT NULL,
    external_modified_at timestamp with time zone NOT NULL,
    urgency_score integer,
    auto_resolved_stale boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_csc_conflict_type CHECK ((conflict_type = ANY (ARRAY['modified_modified'::text, 'deleted_modified'::text, 'modified_deleted'::text]))),
    CONSTRAINT ck_resolution CHECK (((resolution IS NULL) OR (resolution = ANY (ARRAY['accept_local'::text, 'accept_remote'::text, 'restore_from_calendar'::text, 'delete_calendar_too'::text, 'recreate_calendar_event'::text, 'delete_pilot_job'::text]))))
);


--
-- Name: calendar_sync_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.calendar_sync_log (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    direction text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid NOT NULL,
    external_event_id text,
    status text NOT NULL,
    error_detail jsonb,
    payload_snapshot jsonb,
    CONSTRAINT ck_direction CHECK ((direction = ANY (ARRAY['push'::text, 'pull'::text]))),
    CONSTRAINT ck_entity_type CHECK ((entity_type = ANY (ARRAY['job'::text, 'availability'::text]))),
    CONSTRAINT ck_status CHECK ((status = ANY (ARRAY['success'::text, 'conflict'::text, 'error'::text])))
);


--
-- Name: carrier_fee_schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.carrier_fee_schedule (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fee_code text NOT NULL,
    entity_type text NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    effective_from timestamp with time zone DEFAULT now() NOT NULL,
    effective_to timestamp with time zone,
    amount_millicents bigint NOT NULL,
    CONSTRAINT carrier_fee_schedule_entity_type_chk CHECK ((entity_type = ANY (ARRAY['standard'::text, 'sole_proprietor'::text])))
);


--
-- Name: change_order; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_order (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    description character varying NOT NULL,
    subtotal_cents integer DEFAULT 0 NOT NULL,
    tax_cents integer DEFAULT 0 NOT NULL,
    total_cents integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    client_capture_at timestamp with time zone,
    server_received_at timestamp with time zone
);


--
-- Name: change_order_attachment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_order_attachment (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    change_order_id uuid NOT NULL,
    file_name character varying NOT NULL,
    mime_type character varying NOT NULL,
    size_bytes integer NOT NULL,
    object_key character varying NOT NULL,
    note character varying,
    tenant_id uuid NOT NULL
);


--
-- Name: change_order_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_order_line (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    change_order_id uuid NOT NULL,
    "position" integer NOT NULL,
    qco_line_type_id uuid NOT NULL,
    pricebook_item_id uuid,
    description character varying NOT NULL,
    quantity numeric(12,3) DEFAULT 1 NOT NULL,
    unit character varying,
    unit_price_cents integer DEFAULT 0 NOT NULL,
    supplier_id uuid,
    supplier_item_id uuid,
    taxability_code character varying,
    tax_rate_pct numeric(7,4),
    tax_basis_cents integer,
    tax_amount_cents integer,
    tax_jurisdiction_code character varying,
    tax_as_of timestamp with time zone,
    tax_source character varying,
    total_cents integer DEFAULT 0 NOT NULL,
    subtotal_cents integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL
);


--
-- Name: change_order_line_tax_component; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_order_line_tax_component (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    change_order_line_id uuid NOT NULL,
    tax_rate_version_id bigint NOT NULL,
    component_code character varying NOT NULL,
    rate_pct numeric(7,4) NOT NULL,
    amount_cents integer NOT NULL,
    tenant_id uuid NOT NULL
);


--
-- Name: communication_template; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.communication_template (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid,
    template_code character varying NOT NULL,
    channel character varying NOT NULL,
    subject text,
    body_template text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT communication_template_channel_chk CHECK (((channel)::text = ANY ((ARRAY['sms'::character varying, 'email'::character varying])::text[]))),
    CONSTRAINT communication_template_email_subject_chk CHECK ((((channel)::text <> 'email'::text) OR (subject IS NOT NULL)))
);


--
-- Name: connector_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connector_config (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    mode character varying DEFAULT 'api'::character varying NOT NULL,
    schedule_cron character varying,
    enabled boolean DEFAULT true NOT NULL,
    last_success_at timestamp with time zone,
    failure_count integer DEFAULT 0 NOT NULL,
    contextdata jsonb,
    CONSTRAINT connector_config_mode_chk CHECK (((mode)::text = ANY ((ARRAY['api'::character varying, 'scrape'::character varying, 'manual'::character varying])::text[])))
);


--
-- Name: connector_run_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connector_run_log (
    created_at timestamp with time zone NOT NULL,
    id bigint NOT NULL,
    supplier_id uuid NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    status character varying DEFAULT 'running'::character varying NOT NULL,
    items_fetched integer DEFAULT 0 NOT NULL,
    error character varying,
    contextdata jsonb,
    CONSTRAINT connector_run_log_status_chk CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'success'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: connector_run_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.connector_run_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connector_run_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.connector_run_log_id_seq OWNED BY public.connector_run_log.id;


--
-- Name: contact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    customer_id uuid,
    first_name character varying,
    last_name character varying,
    email public.citext,
    mobile_phone character varying,
    locale character varying,
    timezone character varying,
    notes character varying,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    CONSTRAINT contact_email_format_chk CHECK (((email IS NULL) OR (email OPERATOR(public.~*) '^[^@\s]+@[^@\s]+\.[^@\s]+$'::public.citext)))
);


--
-- Name: contact_endpoint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_endpoint (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    contact_id uuid NOT NULL,
    channel character varying NOT NULL,
    value character varying NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    verification_status character varying DEFAULT 'pending'::character varying NOT NULL,
    verified_at timestamp with time zone,
    consent_status character varying DEFAULT 'unknown'::character varying NOT NULL,
    consent_updated_at timestamp with time zone,
    contextdata jsonb,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    CONSTRAINT contact_endpoint_channel_chk CHECK (((channel)::text = ANY ((ARRAY['email'::character varying, 'sms'::character varying])::text[]))),
    CONSTRAINT contact_endpoint_consent_status_chk CHECK (((consent_status)::text = ANY ((ARRAY['unknown'::character varying, 'opted_in'::character varying, 'opted_out'::character varying])::text[]))),
    CONSTRAINT contact_endpoint_email_format_chk CHECK ((((channel)::text <> 'email'::text) OR ((value)::text ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text))),
    CONSTRAINT contact_endpoint_verification_status_chk CHECK (((verification_status)::text = ANY ((ARRAY['pending'::character varying, 'verified'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: contact_portal_invite; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_portal_invite (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    contact_id uuid NOT NULL,
    email public.citext NOT NULL,
    token_hash character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    invited_by uuid,
    tenant_id uuid NOT NULL,
    CONSTRAINT contact_portal_invite_email_chk CHECK ((email OPERATOR(public.~*) '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::public.citext))
);


--
-- Name: contact_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    tenant_id uuid,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: conversation_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_message (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    role character varying NOT NULL,
    content_text character varying NOT NULL,
    audio_object_key character varying,
    embedding public.vector(1024),
    created_by uuid,
    created_at timestamp with time zone NOT NULL,
    tenant_id uuid NOT NULL,
    structured_content_json jsonb,
    CONSTRAINT conv_msg_role_chk CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying, 'system'::character varying])::text[])))
);


--
-- Name: conversation_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_session (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    status character varying DEFAULT 'active'::character varying NOT NULL,
    context_summary character varying,
    context_embedding public.vector(1024),
    context_window_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    expires_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    title text,
    title_auto_generated boolean DEFAULT false NOT NULL,
    archived_at timestamp with time zone,
    CONSTRAINT conv_session_status_chk CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'ended'::character varying, 'abandoned'::character varying, 'expired'::character varying, 'archived'::character varying])::text[])))
);


--
-- Name: currency; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.currency (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying(3) NOT NULL,
    name character varying NOT NULL,
    symbol character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: customer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    type text DEFAULT 'person'::text NOT NULL,
    display_name character varying NOT NULL,
    first_name character varying,
    last_name character varying,
    company_name character varying,
    dba_name character varying,
    email public.citext,
    mobile_phone character varying,
    locale character varying,
    timezone character varying,
    notes character varying,
    is_active boolean DEFAULT true NOT NULL,
    lifecycle_status_id uuid,
    preferred_contact_channel character varying(10) DEFAULT 'sms'::character varying NOT NULL,
    sms_opted_out boolean DEFAULT false NOT NULL,
    sms_opt_out_at timestamp with time zone,
    sms_opt_in_consent boolean DEFAULT false NOT NULL,
    sms_opt_in_at timestamp with time zone,
    sms_opt_in_source text,
    last_assigned_tech_id uuid,
    taxability_code character varying,
    sms_consent_attested_by uuid,
    sms_consent_attested_at timestamp with time zone,
    sms_consent_ip_address text,
    sms_verification_status text DEFAULT 'unverified'::text,
    card_required boolean DEFAULT false NOT NULL,
    CONSTRAINT customer_email_format_chk CHECK (((email IS NULL) OR (email OPERATOR(public.~*) '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::public.citext))),
    CONSTRAINT customer_preferred_contact_channel_chk CHECK (((preferred_contact_channel)::text = ANY ((ARRAY['sms'::character varying, 'email'::character varying])::text[]))),
    CONSTRAINT customer_sms_opt_in_source_chk CHECK (((sms_opt_in_source IS NULL) OR (sms_opt_in_source = ANY (ARRAY['explicit_checkbox'::text, 'inbound_initiated'::text, 'verbal_captured'::text])))),
    CONSTRAINT customer_sms_verification_status_check CHECK ((sms_verification_status = ANY (ARRAY['unverified'::text, 'pending_verification'::text, 'verified'::text, 'opted_out'::text]))),
    CONSTRAINT customer_type_chk CHECK ((type = ANY (ARRAY['person'::text, 'company'::text])))
);


--
-- Name: customer_comm_template_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_comm_template_type (
    code character varying NOT NULL,
    slug character varying NOT NULL,
    name character varying NOT NULL,
    description text,
    category character varying NOT NULL,
    preferred_channel character varying,
    initiator character varying DEFAULT 'tech'::character varying NOT NULL,
    requires_approval boolean DEFAULT false NOT NULL,
    send_mode character varying DEFAULT 'manual'::character varying NOT NULL,
    trigger_event character varying,
    is_system boolean DEFAULT true NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT customer_comm_template_type_category_chk CHECK (((category)::text = ANY ((ARRAY['pre_appointment'::character varying, 'quoting'::character varying, 'during_job'::character varying, 'post_job'::character varying, 'relationship'::character varying, 'exception'::character varying])::text[]))),
    CONSTRAINT customer_comm_template_type_initiator_chk CHECK (((initiator)::text = ANY ((ARRAY['tech'::character varying, 'owner'::character varying, 'system'::character varying])::text[]))),
    CONSTRAINT customer_comm_template_type_preferred_channel_chk CHECK (((preferred_channel IS NULL) OR ((preferred_channel)::text = ANY ((ARRAY['sms'::character varying, 'email'::character varying, 'both'::character varying])::text[])))),
    CONSTRAINT customer_comm_template_type_send_mode_chk CHECK (((send_mode)::text = ANY ((ARRAY['manual'::character varying, 'automated'::character varying, 'both'::character varying])::text[])))
);


--
-- Name: customer_communication; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_communication (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    job_id uuid,
    sender_user_id uuid NOT NULL,
    template_code character varying NOT NULL,
    template_id uuid,
    rendered_subject text,
    rendered_message text NOT NULL,
    channel character varying NOT NULL,
    customer_preferred_channel character varying(10),
    actual_channel character varying NOT NULL,
    channel_override_flag boolean DEFAULT false NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    sent_at timestamp with time zone,
    notification_outbox_id uuid,
    variables_json jsonb,
    thread_id uuid,
    CONSTRAINT customer_communication_actual_channel_chk CHECK (((actual_channel)::text = ANY ((ARRAY['sms'::character varying, 'email'::character varying])::text[]))),
    CONSTRAINT customer_communication_channel_chk CHECK (((channel)::text = ANY ((ARRAY['sms'::character varying, 'email'::character varying])::text[]))),
    CONSTRAINT customer_communication_status_chk CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'sent'::character varying, 'failed'::character varying, 'canceled'::character varying])::text[])))
);


--
-- Name: customer_communication_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_communication_message (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    thread_id uuid NOT NULL,
    direction text NOT NULL,
    channel text DEFAULT 'sms'::text NOT NULL,
    body text NOT NULL,
    segment_count integer DEFAULT 1 NOT NULL,
    status text DEFAULT 'pending_send'::text NOT NULL,
    carrier_message_id text,
    sent_at timestamp with time zone,
    delivered_at timestamp with time zone,
    received_at timestamp with time zone,
    composition_method text,
    template_id uuid,
    voice_audio_id bigint,
    audit_user_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT customer_communication_message_channel_chk CHECK ((channel = 'sms'::text)),
    CONSTRAINT customer_communication_message_composition_method_chk CHECK (((composition_method IS NULL) OR (composition_method = ANY (ARRAY['template'::text, 'free_form_text'::text, 'free_form_voice'::text])))),
    CONSTRAINT customer_communication_message_direction_chk CHECK ((direction = ANY (ARRAY['outbound'::text, 'inbound'::text]))),
    CONSTRAINT customer_communication_message_status_chk CHECK ((status = ANY (ARRAY['pending_send'::text, 'sent'::text, 'delivered'::text, 'failed'::text, 'received'::text])))
);


--
-- Name: customer_communication_message_read_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_communication_message_read_state (
    message_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by uuid
);


--
-- Name: customer_communication_thread; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_communication_thread (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    tech_id uuid NOT NULL,
    tenant_phone_number_id uuid NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    first_message_at timestamp with time zone NOT NULL,
    last_message_at timestamp with time zone NOT NULL,
    message_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT customer_communication_thread_status_chk CHECK ((status = ANY (ARRAY['active'::text, 'archived'::text])))
);


--
-- Name: customer_communication_unrouted; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_communication_unrouted (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    from_number text NOT NULL,
    to_number text NOT NULL,
    body text NOT NULL,
    carrier_message_id text,
    received_at timestamp with time zone NOT NULL,
    parked_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    resolved_by uuid,
    resolved_thread_id uuid,
    status text DEFAULT 'parked'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT customer_communication_unrouted_status_chk CHECK ((status = ANY (ARRAY['parked'::text, 'assigned'::text, 'dismissed'::text])))
);


--
-- Name: customer_lifecycle_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_lifecycle_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: customer_sms_consent_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_sms_consent_audit (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    attested_by uuid NOT NULL,
    ip_address text NOT NULL,
    attested_at timestamp with time zone NOT NULL,
    consent_text_hash text NOT NULL,
    action text NOT NULL,
    created_by uuid,
    CONSTRAINT customer_sms_consent_audit_action_chk CHECK ((action = ANY (ARRAY['attested'::text, 'double_opt_in_sent'::text, 'double_opt_in_confirmed'::text, 'opted_out'::text])))
);


--
-- Name: data_export_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_export_request (
    export_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    s3_path text,
    signed_url text,
    expires_at timestamp with time zone,
    data_scope text NOT NULL,
    failure_reason text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: discount_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discount_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    pct_off numeric(6,3),
    amount_off_cents integer,
    valid_period tstzrange NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT discount_version_value_check CHECK ((((pct_off IS NOT NULL) AND (amount_off_cents IS NULL)) OR ((pct_off IS NULL) AND (amount_off_cents IS NOT NULL))))
);


--
-- Name: discount_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.discount_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: discount_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.discount_version_id_seq OWNED BY public.discount_version.id;


--
-- Name: email_template; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_template (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    template_id text NOT NULL,
    display_name text NOT NULL,
    category text NOT NULL,
    subject_template text NOT NULL,
    body_html_template text NOT NULL,
    body_plain_template text NOT NULL,
    variables jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT email_template_category_chk CHECK ((category = ANY (ARRAY['customer_facing'::text, 'internal'::text])))
);


--
-- Name: entity_address; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_address (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    entity_type_code character varying NOT NULL,
    entity_id uuid NOT NULL,
    address_id uuid NOT NULL,
    address_type_code character varying NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL
);


--
-- Name: entity_contact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_contact (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    entity_type_code character varying NOT NULL,
    entity_id uuid NOT NULL,
    contact_id uuid NOT NULL,
    contact_type_code character varying NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    tenant_id uuid NOT NULL
);


--
-- Name: entity_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_default boolean DEFAULT false NOT NULL
);


--
-- Name: feedback_submission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.feedback_submission (
    submission_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    category text NOT NULL,
    body text NOT NULL,
    from_help_chat_session_id uuid,
    email_sent_to text NOT NULL,
    email_message_id text,
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    CONSTRAINT feedback_submission_category_chk CHECK ((category = ANY (ARRAY['bug'::text, 'feature_request'::text, 'question'::text, 'general'::text])))
);


--
-- Name: help_article; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_article (
    code text NOT NULL,
    s3_path text NOT NULL,
    title text NOT NULL,
    category text NOT NULL,
    frontmatter_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    last_content_hash text NOT NULL,
    last_processed_at timestamp with time zone NOT NULL,
    last_updated date NOT NULL,
    audience text[] DEFAULT '{}'::text[] NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: help_article_chunk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_article_chunk (
    chunk_id uuid DEFAULT gen_random_uuid() NOT NULL,
    article_id text NOT NULL,
    chunk_order integer NOT NULL,
    section_title text NOT NULL,
    chunk_text text NOT NULL,
    chunk_text_with_metadata text NOT NULL,
    embedding public.vector(1536) NOT NULL,
    token_count integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: help_chat_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_chat_message (
    message_id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    context_payload jsonb,
    retrieved_chunks jsonb,
    voice_used boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    CONSTRAINT help_chat_message_role_chk CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text])))
);


--
-- Name: help_chat_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_chat_session (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    started_at timestamp with time zone NOT NULL,
    last_activity_at timestamp with time zone NOT NULL,
    title text,
    outcome text,
    message_count integer DEFAULT 0 NOT NULL,
    anonymized_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT help_chat_session_outcome_chk CHECK ((outcome = ANY (ARRAY['resolved'::text, 'escalated'::text, 'abandoned'::text])))
);


--
-- Name: help_training_corpus; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_training_corpus (
    corpus_id uuid DEFAULT gen_random_uuid() NOT NULL,
    original_session_id_hash text NOT NULL,
    anonymized_message_history jsonb NOT NULL,
    anonymized_context_payload jsonb,
    category_inferred text,
    outcome text NOT NULL,
    anonymized_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: idempotency_key; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.idempotency_key (
    created_at timestamp with time zone NOT NULL,
    key character varying NOT NULL,
    tenant_id uuid,
    user_id uuid,
    first_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    status character varying DEFAULT 'in_progress'::character varying NOT NULL,
    request_hash character varying,
    response_hash character varying,
    response_body jsonb,
    locked_until timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    CONSTRAINT idempotency_key_status_chk CHECK (((status)::text = ANY ((ARRAY['in_progress'::character varying, 'succeeded'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: in_app_notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.in_app_notification (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    category_id text NOT NULL,
    body text NOT NULL,
    deep_link_target text NOT NULL,
    priority text DEFAULT 'standard'::text NOT NULL,
    read_at timestamp with time zone,
    CONSTRAINT chk_in_app_notif_priority CHECK ((priority = ANY (ARRAY['standard'::text, 'critical'::text])))
);


--
-- Name: integration_credential; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integration_credential (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    app_service_id uuid NOT NULL,
    secret_json jsonb NOT NULL,
    rotated_at timestamp with time zone,
    expires_at timestamp with time zone,
    last_refresh_at timestamp with time zone,
    connected_at timestamp with time zone,
    disconnected_at timestamp with time zone,
    initiated_by_user_id uuid,
    connection_status character varying DEFAULT 'pending'::character varying NOT NULL,
    CONSTRAINT ck_integration_credential_status CHECK (((connection_status)::text = ANY ((ARRAY['pending'::character varying, 'active'::character varying, 'disconnected'::character varying, 'expired'::character varying, 'revoked'::character varying])::text[])))
);


--
-- Name: integration_sync_conflict; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integration_sync_conflict (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    app_service_id uuid NOT NULL,
    entity_type_code character varying NOT NULL,
    entity_id uuid NOT NULL,
    external_id character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    internal_payload jsonb NOT NULL,
    external_payload jsonb NOT NULL,
    resolved_at timestamp with time zone,
    resolved_by uuid,
    base_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    field_diffs jsonb DEFAULT '[]'::jsonb NOT NULL,
    pilot_modified_at timestamp with time zone DEFAULT now() NOT NULL,
    pilot_modified_by_user_id uuid,
    qb_modified_at timestamp with time zone DEFAULT now() NOT NULL,
    qb_modified_by_external_user_label text,
    auto_expire_at timestamp with time zone,
    pre_warning_at timestamp with time zone,
    conflict_subtype character varying,
    financial_delta_payload jsonb,
    CONSTRAINT integration_sync_conflict_status_chk CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'resolved_keep_internal'::character varying, 'resolved_keep_external'::character varying])::text[]))),
    CONSTRAINT integration_sync_conflict_subtype_chk CHECK (((conflict_subtype IS NULL) OR ((conflict_subtype)::text = ANY ((ARRAY['customer'::character varying, 'quote'::character varying, 'invoice'::character varying, 'expense'::character varying, 'deletion_local'::character varying, 'deletion_remote'::character varying, 'display_name_dedup'::character varying])::text[]))))
);


--
-- Name: integration_sync_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integration_sync_log (
    created_at timestamp with time zone NOT NULL,
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    app_service_id uuid NOT NULL,
    status character varying NOT NULL,
    started_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone NOT NULL,
    records_processed integer DEFAULT 0 NOT NULL,
    records_failed integer DEFAULT 0 NOT NULL,
    error_message character varying,
    contextdata jsonb,
    created_by uuid,
    CONSTRAINT isl_status_chk CHECK (((status)::text = ANY ((ARRAY['success'::character varying, 'failed'::character varying, 'partial_success'::character varying])::text[])))
);


--
-- Name: integration_sync_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.integration_sync_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: integration_sync_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.integration_sync_log_id_seq OWNED BY public.integration_sync_log.id;


--
-- Name: integration_sync_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integration_sync_mapping (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    app_service_id uuid NOT NULL,
    entity_type_code character varying NOT NULL,
    entity_id uuid NOT NULL,
    external_id character varying NOT NULL,
    external_version_token character varying,
    sync_preference character varying DEFAULT 'pilot_master'::character varying NOT NULL,
    last_synced_at timestamp with time zone DEFAULT now() NOT NULL,
    internal_version_token character varying,
    CONSTRAINT sync_preference_chk CHECK (((sync_preference)::text = ANY ((ARRAY['pilot_master'::character varying, 'external_master'::character varying, 'bi_directional'::character varying])::text[])))
);


--
-- Name: invoice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_number character varying NOT NULL,
    quote_id uuid,
    job_id uuid,
    customer_id uuid NOT NULL,
    site_id uuid NOT NULL,
    status_id uuid NOT NULL,
    idempotency_key character varying,
    issued_at timestamp with time zone,
    due_at timestamp with time zone,
    subtotal_cents integer DEFAULT 0 NOT NULL,
    tax_cents integer DEFAULT 0 NOT NULL,
    total_cents integer DEFAULT 0 NOT NULL,
    balance_due_cents integer DEFAULT 0 NOT NULL,
    currency character varying(3) DEFAULT 'USD'::character varying NOT NULL,
    customer_notes character varying,
    terms_and_conditions character varying,
    pdf_object_key character varying,
    is_active boolean DEFAULT true NOT NULL,
    last_reminder_sent_at timestamp with time zone,
    reminder_count integer DEFAULT 0 NOT NULL,
    payment_terms character varying(30),
    billing_mode character varying(20) DEFAULT 'line_item'::character varying NOT NULL,
    progress_pct numeric(5,2),
    internal_memo text,
    payment_schedule_line_id uuid,
    CONSTRAINT chk_invoice_billing_mode CHECK (((billing_mode)::text = ANY ((ARRAY['line_item'::character varying, 'progress'::character varying])::text[]))),
    CONSTRAINT chk_invoice_payment_terms CHECK (((payment_terms)::text = ANY ((ARRAY['due_on_receipt'::character varying, 'net_15'::character varying, 'net_30'::character varying, 'custom_date'::character varying])::text[])))
);


--
-- Name: invoice_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_line (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    source_type character varying NOT NULL,
    source_id uuid,
    "position" integer NOT NULL,
    qco_line_type_id uuid NOT NULL,
    pricebook_item_id uuid,
    description character varying NOT NULL,
    quantity numeric(12,3) DEFAULT 1 NOT NULL,
    unit character varying,
    unit_price_cents integer DEFAULT 0 NOT NULL,
    taxability_code character varying,
    tax_rate_pct numeric(7,4),
    tax_basis_cents integer,
    tax_amount_cents integer,
    tax_jurisdiction_code character varying,
    tax_as_of timestamp with time zone,
    tax_source character varying,
    subtotal_cents integer DEFAULT 0 NOT NULL,
    total_cents integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    CONSTRAINT invoice_line_source_type_chk CHECK (((source_type)::text = ANY ((ARRAY['quote_line'::character varying, 'change_order_line'::character varying, 'ad_hoc'::character varying])::text[])))
);


--
-- Name: invoice_line_tax_component; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_line_tax_component (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    invoice_line_id uuid NOT NULL,
    tax_rate_version_id bigint NOT NULL,
    component_code character varying NOT NULL,
    rate_pct numeric(7,4) NOT NULL,
    amount_cents integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL
);


--
-- Name: invoice_public_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_public_link (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    contact_id uuid,
    token_hash character varying NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '90 days'::interval) NOT NULL,
    max_uses integer DEFAULT 0 NOT NULL,
    used_count integer DEFAULT 0 NOT NULL,
    status character varying DEFAULT 'active'::character varying NOT NULL,
    last_used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    signed_token text DEFAULT 'legacy.placeholder'::text NOT NULL,
    revoked_at timestamp with time zone,
    created_by_user_id uuid,
    CONSTRAINT invoice_public_link_status_chk CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'revoked'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: invoice_signoff; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_signoff (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    signed_by_name character varying(200) NOT NULL,
    signature_object_key character varying(500) NOT NULL,
    terms_acknowledged boolean DEFAULT false NOT NULL,
    signed_at timestamp with time zone DEFAULT now() NOT NULL,
    client_capture_at timestamp with time zone,
    captured_by_user_id uuid NOT NULL,
    superseded_at timestamp with time zone,
    idempotency_key character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT ck_invoice_signoff_terms CHECK ((terms_acknowledged = true))
);


--
-- Name: invoice_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_terminal boolean DEFAULT false NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    quote_id uuid,
    quote_version_id uuid,
    customer_id uuid NOT NULL,
    site_id uuid NOT NULL,
    status_id uuid NOT NULL,
    scheduled_start_at timestamp with time zone,
    scheduled_end_at timestamp with time zone,
    actual_labor_cost_cents integer DEFAULT 0 NOT NULL,
    actual_material_cost_cents integer DEFAULT 0 NOT NULL,
    actual_profit_cents integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    estimated_duration_minutes integer,
    external_calendar_event_id text,
    version integer DEFAULT 1 NOT NULL,
    variance_owner_notified_at timestamp with time zone,
    variance_last_notified_pct numeric(5,1),
    job_number character varying(30) NOT NULL,
    recurrence_rule_id uuid,
    priority text DEFAULT 'standard'::text NOT NULL,
    job_type_id uuid,
    title text,
    CONSTRAINT ck_job_estimated_duration_positive CHECK (((estimated_duration_minutes IS NULL) OR (estimated_duration_minutes > 0))),
    CONSTRAINT ck_job_schedule_range CHECK ((((scheduled_start_at IS NULL) AND (scheduled_end_at IS NULL)) OR ((scheduled_start_at IS NOT NULL) AND (scheduled_end_at IS NOT NULL) AND (scheduled_end_at > scheduled_start_at)))),
    CONSTRAINT job_priority_chk CHECK ((priority = ANY (ARRAY['standard'::text, 'urgent'::text, 'emergency'::text])))
);


--
-- Name: job_attachment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_attachment (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    job_id uuid NOT NULL,
    file_name character varying NOT NULL,
    mime_type character varying NOT NULL,
    size_bytes integer NOT NULL,
    object_key character varying NOT NULL,
    description character varying,
    client_capture_at timestamp with time zone,
    file_hash text,
    upload_status text,
    s3_upload_session_id text,
    upload_completed_at timestamp with time zone,
    expense_id uuid,
    server_received_at timestamp with time zone,
    CONSTRAINT chk_job_attachment_upload_status CHECK (((upload_status IS NULL) OR (upload_status = ANY (ARRAY['pending_upload'::text, 'uploading'::text, 'complete'::text, 'failed'::text]))))
);


--
-- Name: job_expense; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_expense (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    job_id uuid NOT NULL,
    job_expense_category_code character varying NOT NULL,
    description character varying NOT NULL,
    vendor_name character varying,
    incurred_at timestamp with time zone DEFAULT now() NOT NULL,
    cost_cents integer NOT NULL,
    markup_pct numeric(7,4) DEFAULT 0 NOT NULL,
    markup_amt_cents integer,
    billable_cents integer NOT NULL,
    is_billable boolean DEFAULT true NOT NULL,
    invoice_line_id uuid,
    receipt_object_key character varying,
    is_active boolean DEFAULT true NOT NULL,
    client_capture_at timestamp with time zone,
    server_received_at timestamp with time zone,
    user_id uuid NOT NULL,
    ocr_processed_at timestamp with time zone,
    ocr_source character varying
);


--
-- Name: job_expense_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_expense_category (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    tenant_id uuid,
    name character varying NOT NULL,
    description character varying,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: job_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_notes (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    notes character varying NOT NULL,
    audio_object_key character varying,
    customer_visible boolean DEFAULT false NOT NULL,
    tenant_id uuid NOT NULL,
    client_capture_at timestamp with time zone,
    server_received_at timestamp with time zone
);


--
-- Name: job_recurrence_rule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_recurrence_rule (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    site_id uuid NOT NULL,
    pattern character varying(20) NOT NULL,
    interval_count integer DEFAULT 1 NOT NULL,
    starts_on date NOT NULL,
    ends_on date,
    max_occurrences integer,
    occurrences_created integer DEFAULT 0 NOT NULL,
    next_job_at timestamp with time zone,
    last_job_created_at timestamp with time zone,
    estimated_duration_minutes integer,
    default_tech_user_id uuid,
    notes_template text,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT chk_interval_count_positive CHECK ((interval_count >= 1)),
    CONSTRAINT chk_recurrence_pattern CHECK (((pattern)::text = ANY ((ARRAY['daily'::character varying, 'weekly'::character varying, 'monthly'::character varying, 'annually'::character varying])::text[])))
);


--
-- Name: job_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_terminal boolean DEFAULT false NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: job_tech_assignment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_tech_assignment (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    job_id uuid NOT NULL,
    user_id uuid NOT NULL,
    assigned_by_user_id uuid NOT NULL,
    role text DEFAULT 'primary'::text NOT NULL,
    ordinal integer DEFAULT 1 NOT NULL,
    assigned_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_ordinal_positive CHECK ((ordinal >= 1)),
    CONSTRAINT ck_role_valid CHECK ((role = ANY (ARRAY['primary'::text, 'helper'::text])))
);


--
-- Name: job_time_entry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_time_entry (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    user_id uuid NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    hours numeric(10,3),
    notes character varying,
    hourly_rate_cents integer NOT NULL,
    total_cost_cents integer NOT NULL,
    tenant_id uuid NOT NULL,
    check_in_lat numeric(10,7),
    check_in_lng numeric(10,7),
    gps_variance_meters integer,
    hours_remaining_estimate numeric(6,2),
    hours_remaining_was_overridden boolean,
    override_note text,
    quote_line_id uuid,
    etc_captured_at timestamp with time zone,
    client_capture_at timestamp with time zone,
    server_received_at timestamp with time zone
);


--
-- Name: job_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code text NOT NULL,
    label text NOT NULL,
    sort_order integer DEFAULT 100 NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: jwk_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jwk_status (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_signable boolean DEFAULT false NOT NULL
);


--
-- Name: labor_rate_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.labor_rate_version (
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    skill_level_code character varying NOT NULL,
    hourly_rate_cents integer NOT NULL,
    burden_pct numeric(7,4) NOT NULL,
    valid_period tstzrange DEFAULT tstzrange(now(), NULL::timestamp with time zone, '[)'::text) NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    CONSTRAINT labor_rate_version_valid_period_chk CHECK ((NOT isempty(valid_period)))
);


--
-- Name: labor_rate_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.labor_rate_version ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.labor_rate_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: loto_confirmation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.loto_confirmation (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    job_id uuid NOT NULL,
    user_id uuid NOT NULL,
    confirmed_at timestamp with time zone NOT NULL,
    client_capture_at timestamp with time zone,
    server_received_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: marketing_contact_submission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marketing_contact_submission (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying NOT NULL,
    email public.citext NOT NULL,
    company character varying,
    trade character varying,
    subject character varying NOT NULL,
    message text NOT NULL,
    source_page character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_read boolean DEFAULT false NOT NULL
);


--
-- Name: marketing_job_application; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marketing_job_application (
    id uuid NOT NULL,
    name character varying NOT NULL,
    email character varying NOT NULL,
    role character varying NOT NULL,
    linkedin_url character varying,
    portfolio_url character varying,
    why_interested text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_reviewed boolean DEFAULT false NOT NULL
);


--
-- Name: marketing_newsletter_subscriber; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marketing_newsletter_subscriber (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email public.citext NOT NULL,
    trade_interest character varying[],
    content_preferences character varying[],
    source character varying,
    utm_source character varying,
    utm_medium character varying,
    utm_campaign character varying,
    subscribed_at timestamp with time zone DEFAULT now() NOT NULL,
    unsubscribed_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: marketing_waitlist_signup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marketing_waitlist_signup (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email public.citext NOT NULL,
    trade character varying NOT NULL,
    company_size character varying NOT NULL,
    source character varying NOT NULL,
    utm_source character varying,
    utm_medium character varying,
    utm_campaign character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    converted_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    name character varying,
    state character varying,
    notes text
);


--
-- Name: mfa_grace_period_tracking; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mfa_grace_period_tracking (
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    grace_started_at timestamp with time zone NOT NULL,
    enrolled_at timestamp with time zone,
    enforcement_activated_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: mobile_device_push_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_device_push_token (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    device_id uuid NOT NULL,
    platform text NOT NULL,
    push_token text NOT NULL,
    app_version text,
    os_version text,
    registered_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    notification_permission_granted boolean DEFAULT true NOT NULL,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT mobile_device_push_token_platform_chk CHECK ((platform = ANY (ARRAY['ios'::text, 'android'::text])))
);


--
-- Name: mobile_push_permission_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_push_permission_state (
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    device_id uuid NOT NULL,
    permission_state text DEFAULT 'not_asked'::text NOT NULL,
    last_state_change_at timestamp with time zone NOT NULL,
    dismissable_banner_dismissed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT mobile_push_permission_state_state_chk CHECK ((permission_state = ANY (ARRAY['not_asked'::text, 'granted'::text, 'denied_by_user_choice'::text, 'denied_by_os'::text, 'revoked_in_settings'::text])))
);


--
-- Name: mobile_push_rate_limit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_push_rate_limit (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    device_id uuid NOT NULL,
    last_push_sent_at timestamp with time zone DEFAULT now() NOT NULL,
    push_count_current_window integer DEFAULT 1 NOT NULL,
    window_start_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: mobile_sync_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_sync_event (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    device_id text NOT NULL,
    operation_type text NOT NULL,
    operation_payload_summary jsonb,
    status text NOT NULL,
    conflict_severity text,
    client_capture_at timestamp with time zone NOT NULL,
    synced_at timestamp with time zone,
    error_detail jsonb,
    idempotency_uuid uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    resolution_action text,
    CONSTRAINT chk_mobile_sync_event_conflict_severity CHECK (((conflict_severity IS NULL) OR (conflict_severity = ANY (ARRAY['auto_silent'::text, 'auto_notice'::text, 'tech_resolvable'::text, 'owner_escalation'::text])))),
    CONSTRAINT chk_mobile_sync_event_resolution_action CHECK (((resolution_action IS NULL) OR (resolution_action = ANY (ARRAY['use_local'::text, 'use_server'::text, 'escalate_to_owner'::text])))),
    CONSTRAINT chk_mobile_sync_event_status CHECK ((status = ANY (ARRAY['pending'::text, 'syncing'::text, 'succeeded'::text, 'failed'::text, 'conflict'::text])))
);


--
-- Name: mobile_sync_event_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_sync_event_audit (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    escalation_id uuid NOT NULL,
    originator_user_id uuid NOT NULL,
    resolver_user_id uuid NOT NULL,
    resolution_action text NOT NULL,
    resolution_channel text DEFAULT 'web'::text NOT NULL,
    tech_local_snapshot_at_commit jsonb,
    server_state_snapshot_at_commit jsonb,
    post_commit_state jsonb,
    resolved_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    CONSTRAINT mobile_sync_event_audit_channel_chk CHECK ((resolution_channel = ANY (ARRAY['web'::text, 'voice'::text])))
);


--
-- Name: mobile_sync_owner_escalation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_sync_owner_escalation (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    originating_user_id uuid NOT NULL,
    conflict_id uuid NOT NULL,
    escalated_at timestamp with time zone DEFAULT now() NOT NULL,
    escalation_reason text NOT NULL,
    escalation_reason_explainer text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    resolved_by_user_id uuid,
    resolved_at timestamp with time zone,
    resolution_action text,
    resolution_payload jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT chk_mobile_sync_escalation_reason CHECK ((escalation_reason = ANY (ARRAY['auto_severity'::text, 'tech_chose'::text]))),
    CONSTRAINT chk_mobile_sync_escalation_resolution_action CHECK (((resolution_action IS NULL) OR (resolution_action = ANY (ARRAY['used_local'::text, 'used_server'::text, 'manual_edit'::text, 'rejected'::text, 'use_tech'::text, 'use_server'::text, 'restore_and_accept'::text, 'override_with_tech'::text, 'discard_tech'::text, 'accept_authorized_at_capture'::text, 'reject_unauthorized'::text])))),
    CONSTRAINT chk_mobile_sync_escalation_status CHECK ((status = ANY (ARRAY['pending'::text, 'resolved'::text, 'rejected'::text, 'auto_recovered'::text, 'stale'::text])))
);


--
-- Name: mobile_sync_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mobile_sync_session (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    device_id uuid NOT NULL,
    triggered_by text NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    outcome text,
    items_attempted integer DEFAULT 0 NOT NULL,
    items_committed integer DEFAULT 0 NOT NULL,
    items_deferred integer DEFAULT 0 NOT NULL,
    items_failed integer DEFAULT 0 NOT NULL,
    failure_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mobile_sync_session_outcome_chk CHECK (((outcome IS NULL) OR (outcome = ANY (ARRAY['success'::text, 'partial'::text, 'failed'::text, 'throttled'::text])))),
    CONSTRAINT mobile_sync_session_triggered_by_chk CHECK ((triggered_by = ANY (ARRAY['silent_push'::text, 'os_opportunistic'::text, 'foreground'::text, 'manual'::text])))
);


--
-- Name: nec_calculation_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nec_calculation_log (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    job_id uuid,
    calc_type character varying(50) NOT NULL,
    nec_guide_version character varying(20) DEFAULT '2023'::character varying NOT NULL,
    inputs_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    result_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_offline_calc boolean DEFAULT false NOT NULL,
    idempotency_key uuid,
    client_capture_at timestamp with time zone,
    CONSTRAINT ck_nec_calc_log_tenant_not_null CHECK ((tenant_id IS NOT NULL)),
    CONSTRAINT ck_nec_calc_type CHECK (((calc_type)::text = ANY ((ARRAY['voltage_drop'::character varying, 'conduit_fill'::character varying, 'ampacity'::character varying])::text[])))
);


--
-- Name: notification_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_category (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    code text NOT NULL,
    display_label text NOT NULL,
    description text NOT NULL,
    category_group_id text,
    display_order integer NOT NULL
);


--
-- Name: notification_category_sub_trigger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_category_sub_trigger (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    code text NOT NULL,
    category_id text NOT NULL,
    display_label text,
    forced_minimum_push_uniform boolean DEFAULT false NOT NULL,
    forced_minimum_push_recipient_only boolean DEFAULT false
);


--
-- Name: notification_channel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_channel (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: notification_default_policy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_default_policy (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid,
    category_id text NOT NULL,
    channel text NOT NULL,
    enabled boolean NOT NULL,
    CONSTRAINT chk_notif_default_policy_channel CHECK ((channel = ANY (ARRAY['push'::text, 'email'::text, 'in_app'::text])))
);


--
-- Name: notification_delivery_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_delivery_attempt (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id bigint NOT NULL,
    notification_outbox_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    attempt_no integer NOT NULL,
    status character varying NOT NULL,
    provider character varying NOT NULL,
    details jsonb,
    error_message character varying,
    http_status integer,
    attempted_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    next_attempt_after timestamp with time zone,
    retryable boolean DEFAULT true NOT NULL,
    provider_code character varying,
    duration_ms integer,
    created_by uuid,
    CONSTRAINT notification_delivery_attempt_status_chk CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'delivered'::character varying, 'bounced'::character varying, 'rejected'::character varying, 'throttled'::character varying, 'error'::character varying])::text[])))
);


--
-- Name: notification_delivery_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_delivery_attempt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_delivery_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_delivery_attempt_id_seq OWNED BY public.notification_delivery_attempt.id;


--
-- Name: notification_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_event (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    notification_type_code character varying NOT NULL,
    entity_type_code character varying NOT NULL,
    entity_id character varying NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    payload jsonb
);


--
-- Name: notification_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_outbox (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    notification_event_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    recipient_contact_id uuid,
    recipient_user_id uuid,
    channel character varying NOT NULL,
    contact_endpoint_id uuid,
    user_endpoint_id uuid,
    to_address character varying,
    subject character varying,
    body character varying NOT NULL,
    scheduled_at timestamp with time zone,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    provider_message_id character varying,
    idempotency_key character varying,
    attempt_count integer DEFAULT 0 NOT NULL,
    next_attempt_at timestamp with time zone,
    last_error character varying,
    priority integer DEFAULT 5 NOT NULL,
    contextdata jsonb,
    category_id text NOT NULL,
    sub_trigger_id text,
    recipient_user_id_originating uuid,
    CONSTRAINT notification_outbox_inapp_requires_user_chk CHECK ((((channel)::text <> 'in_app'::text) OR (recipient_user_id IS NOT NULL))),
    CONSTRAINT notification_outbox_recipient_exclusive_chk CHECK ((((((recipient_contact_id IS NOT NULL))::integer + ((recipient_user_id IS NOT NULL))::integer) + ((to_address IS NOT NULL))::integer) = 1)),
    CONSTRAINT notification_outbox_recipient_presence_chk CHECK (((recipient_contact_id IS NOT NULL) OR (recipient_user_id IS NOT NULL) OR (to_address IS NOT NULL))),
    CONSTRAINT notification_outbox_status_chk CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'sent'::character varying, 'failed'::character varying, 'canceled'::character varying, 'suppressed_by_preferences'::character varying])::text[])))
);


--
-- Name: notification_preference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_preference (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid,
    category_id text NOT NULL,
    channel text NOT NULL,
    enabled boolean NOT NULL,
    CONSTRAINT chk_notif_pref_channel CHECK ((channel = ANY (ARRAY['push'::text, 'email'::text, 'in_app'::text])))
);


--
-- Name: notification_template; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_template (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    notification_type_code character varying NOT NULL,
    channel character varying NOT NULL,
    locale character varying NOT NULL,
    subject character varying,
    body character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: notification_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    tenant_id uuid,
    audience character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT notification_type_audience_chk CHECK (((audience)::text = ANY ((ARRAY['tenant'::character varying, 'customer'::character varying])::text[])))
);


--
-- Name: password_policy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_policy (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    min_length integer,
    min_lowercase integer,
    min_uppercase integer,
    min_digits integer,
    min_special integer,
    history_depth integer,
    lockout_threshold integer,
    lockout_window_minutes integer,
    lockout_duration_minutes integer,
    require_mfa boolean,
    rotation_days integer
);


--
-- Name: payment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    amount_cents integer NOT NULL,
    payment_method_id uuid NOT NULL,
    status_id uuid NOT NULL,
    paid_at timestamp with time zone,
    psp_provider character varying,
    psp_payment_id character varying,
    connector_config_id uuid,
    idempotency_key character varying,
    is_active boolean DEFAULT true NOT NULL,
    stripe_payment_intent_id text,
    customer_payment_comment text,
    amount_variance_cents integer,
    paid_via text,
    variance_resolution character varying(20),
    variance_resolution_note text,
    variance_resolved_at timestamp with time zone,
    variance_resolved_by_user_id uuid,
    CONSTRAINT ck_payment_variance_resolution CHECK (((variance_resolution IS NULL) OR ((variance_resolution)::text = ANY ((ARRAY['credit'::character varying, 'refund_offline'::character varying, 'writeoff'::character varying])::text[])))),
    CONSTRAINT payment_paid_via_chk CHECK ((paid_via = ANY (ARRAY['stripe'::text, 'check'::text, 'bank_transfer'::text, 'other'::text])))
);


--
-- Name: payment_method; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_method (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    payment_type_id uuid NOT NULL,
    brand character varying,
    psp_provider character varying NOT NULL,
    psp_payment_method_id character varying NOT NULL,
    exp_month integer,
    exp_year integer,
    fingerprint character varying,
    billing_address_id uuid,
    name_on_account character varying,
    last4 character varying,
    psp_token character varying,
    customer_id uuid,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: payment_schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_schedule (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    quote_id uuid,
    job_id uuid,
    customer_id uuid NOT NULL,
    site_id uuid NOT NULL,
    contract_total_cents integer NOT NULL,
    status text DEFAULT 'draft'::text NOT NULL,
    basis_default text DEFAULT 'percent'::text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT chk_payment_schedule_basis_default CHECK ((basis_default = ANY (ARRAY['percent'::text, 'fixed_amount'::text]))),
    CONSTRAINT chk_payment_schedule_status CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'completed'::text, 'cancelled'::text])))
);


--
-- Name: payment_schedule_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_schedule_line (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    payment_schedule_id uuid NOT NULL,
    sequence integer NOT NULL,
    label text NOT NULL,
    basis text NOT NULL,
    percent numeric(5,2),
    amount_cents integer,
    trigger_type text DEFAULT 'manual'::text NOT NULL,
    trigger_date date,
    milestone_label text,
    invoice_id uuid,
    status text DEFAULT 'pending'::text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT psl_basis_amount_chk CHECK ((((basis = 'percent'::text) AND (percent IS NOT NULL) AND (amount_cents IS NULL)) OR ((basis = 'fixed_amount'::text) AND (amount_cents IS NOT NULL) AND (percent IS NULL)))),
    CONSTRAINT psl_basis_chk CHECK ((basis = ANY (ARRAY['percent'::text, 'fixed_amount'::text]))),
    CONSTRAINT psl_status_chk CHECK ((status = ANY (ARRAY['pending'::text, 'invoiced'::text, 'paid'::text, 'void'::text]))),
    CONSTRAINT psl_trigger_detail_chk CHECK ((((trigger_type = 'date'::text) AND (trigger_date IS NOT NULL)) OR ((trigger_type = 'milestone'::text) AND (milestone_label IS NOT NULL)) OR (trigger_type = 'manual'::text))),
    CONSTRAINT psl_trigger_type_chk CHECK ((trigger_type = ANY (ARRAY['manual'::text, 'date'::text, 'milestone'::text])))
);


--
-- Name: payment_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_terminal boolean DEFAULT false NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: payment_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: platform_role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_role (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    permissions jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: platform_setting; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_setting (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    key character varying NOT NULL,
    value jsonb NOT NULL,
    tenant_id uuid
);


--
-- Name: platform_setting_catalog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_setting_catalog (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    key character varying NOT NULL,
    label character varying NOT NULL,
    description text,
    value_type character varying NOT NULL,
    tenant_editable boolean DEFAULT false NOT NULL,
    allows_user_override boolean DEFAULT false NOT NULL,
    min_value integer,
    max_value integer,
    allowed_values jsonb,
    category character varying,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    CONSTRAINT ck_platform_setting_catalog_category CHECK (((category)::text = ANY ((ARRAY['quotes'::character varying, 'billing'::character varying, 'notifications'::character varying, 'voice'::character varying, 'qb'::character varying, 'sync'::character varying, 'mobile'::character varying, 'labor'::character varying, 'reports'::character varying, 'security'::character varying, 'trial'::character varying, 'safety'::character varying])::text[]))),
    CONSTRAINT ck_platform_setting_catalog_value_type CHECK (((value_type)::text = ANY ((ARRAY['integer'::character varying, 'boolean'::character varying, 'string'::character varying, 'decimal'::character varying, 'jsonb'::character varying])::text[])))
);


--
-- Name: pricebook_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pricebook_item (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    sku character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    uom_id uuid,
    taxability_code character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: pricebook_item_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pricebook_item_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    pricebook_item_id uuid NOT NULL,
    default_unit_price_cents integer NOT NULL,
    valid_period tstzrange NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT piv_valid_period_chk CHECK ((NOT isempty(valid_period)))
);


--
-- Name: pricebook_item_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pricebook_item_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pricebook_item_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pricebook_item_version_id_seq OWNED BY public.pricebook_item_version.id;


--
-- Name: pricing_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pricing_cache (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    supplier_id uuid NOT NULL,
    sku character varying NOT NULL,
    price_cents integer NOT NULL,
    currency character varying(3) DEFAULT 'USD'::character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    tenant_id uuid,
    id bigint NOT NULL
);


--
-- Name: COLUMN pricing_cache.tenant_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pricing_cache.tenant_id IS 'NULL = global/shared price accessible to all tenants. Non-NULL = private negotiated price for this tenant only. Always filter: tenant_id IS NULL OR tenant_id = current_tenant_id';


--
-- Name: pricing_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pricing_cache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pricing_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pricing_cache_id_seq OWNED BY public.pricing_cache.id;


--
-- Name: product_feature; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_feature (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    unit character varying NOT NULL,
    description character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: product_plan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_plan (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: product_plan_product_feature_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_plan_product_feature_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    product_plan_code character varying NOT NULL,
    product_feature_code character varying NOT NULL,
    limit_quantity integer,
    included_quantity integer,
    overage_price_cents integer,
    valid_period tstzrange NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    limit_enforcement character varying DEFAULT 'block'::character varying NOT NULL,
    overage_cap_per_period integer,
    alert_threshold_pct integer,
    CONSTRAINT chk_pppfv_overage_price_required_when_soft CHECK ((((limit_enforcement)::text = 'block'::text) OR (overage_price_cents IS NOT NULL)))
);


--
-- Name: product_plan_product_feature_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.product_plan_product_feature_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_plan_product_feature_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.product_plan_product_feature_version_id_seq OWNED BY public.product_plan_product_feature_version.id;


--
-- Name: product_plan_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_plan_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    product_plan_code character varying NOT NULL,
    name character varying NOT NULL,
    price_cents integer NOT NULL,
    valid_period tstzrange NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: product_plan_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.product_plan_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_plan_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.product_plan_version_id_seq OWNED BY public.product_plan_version.id;


--
-- Name: psp_customer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.psp_customer (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    psp_provider character varying NOT NULL,
    psp_customer_id character varying NOT NULL
);


--
-- Name: psp_transaction_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.psp_transaction_log (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    payment_id uuid,
    app_service_id uuid NOT NULL,
    transaction_type character varying NOT NULL,
    http_status integer,
    psp_reference_id character varying,
    raw_request jsonb,
    raw_response jsonb,
    error_code character varying
);


--
-- Name: psp_transaction_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.psp_transaction_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: psp_transaction_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.psp_transaction_log_id_seq OWNED BY public.psp_transaction_log.id;


--
-- Name: public_link_short_code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.public_link_short_code (
    created_at timestamp with time zone NOT NULL,
    short_code text NOT NULL,
    link_type text NOT NULL,
    link_id uuid NOT NULL,
    click_count integer DEFAULT 0 NOT NULL,
    last_clicked_at timestamp with time zone,
    created_by uuid,
    CONSTRAINT public_link_short_code_link_type_chk CHECK ((link_type = ANY (ARRAY['quote'::text, 'invoice'::text])))
);


--
-- Name: qco_line_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qco_line_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    qb_item_name_hint character varying
);


--
-- Name: qpl_contact_action_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qpl_contact_action_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: quote; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    site_id uuid NOT NULL,
    status_id uuid NOT NULL,
    subtotal_cents integer DEFAULT 0 NOT NULL,
    tax_cents integer DEFAULT 0 NOT NULL,
    total_cents integer DEFAULT 0 NOT NULL,
    currency character varying(3) DEFAULT 'USD'::character varying NOT NULL,
    idempotency_key character varying,
    is_active boolean DEFAULT true NOT NULL,
    submitted_by_user_id uuid,
    submitted_at timestamp with time zone,
    approved_by_user_id uuid,
    approved_at timestamp with time zone,
    discount_pct numeric(5,2),
    discount_amount_cents integer,
    discount_expires_at timestamp with time zone,
    discount_applied_by_user_id uuid,
    customer_acceptance_comment text,
    customer_accepted_at timestamp with time zone,
    customer_decline_comment text,
    customer_decline_reason text,
    customer_declined_at timestamp with time zone,
    customer_email_at_action text,
    expires_at timestamp with time zone,
    quote_number character varying(20) NOT NULL,
    title character varying(255),
    card_required boolean,
    CONSTRAINT quote_customer_decline_reason_chk CHECK ((customer_decline_reason = ANY (ARRAY['pricing'::text, 'scope'::text, 'timing'::text, 'other_contractor'::text, 'other'::text])))
);


--
-- Name: quote_acceptance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_acceptance (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    quote_version_id uuid NOT NULL,
    contact_id uuid,
    approved_at timestamp with time zone DEFAULT now() NOT NULL,
    approved_ip inet,
    approved_user_agent character varying,
    signature_url character varying,
    terms_acknowledged boolean DEFAULT true NOT NULL,
    accepted_by_name text NOT NULL,
    accepted_by_email public.citext NOT NULL,
    accepted_by_user_id uuid,
    acceptance_notes text,
    quote_public_link_id uuid,
    tenant_id uuid NOT NULL
);


--
-- Name: quote_approval_comment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_approval_comment (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    quote_id uuid NOT NULL,
    quote_version_id uuid NOT NULL,
    target_line_id uuid,
    author_user_id uuid NOT NULL,
    comment_type text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    CONSTRAINT chk_quote_approval_comment_type CHECK ((comment_type = ANY (ARRAY['kickback'::text, 'rejection'::text, 'edit_annotation'::text])))
);


--
-- Name: quote_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_line (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    quote_id uuid NOT NULL,
    "position" integer NOT NULL,
    qco_line_type_id uuid NOT NULL,
    pricebook_item_id uuid,
    description character varying NOT NULL,
    quantity numeric(12,3) DEFAULT 1 NOT NULL,
    unit character varying,
    unit_price_cents integer DEFAULT 0 NOT NULL,
    supplier_id uuid,
    supplier_item_id uuid,
    taxability_code character varying,
    tax_rate_pct numeric(7,4),
    tax_basis_cents integer,
    tax_amount_cents integer,
    tax_jurisdiction_code character varying,
    tax_as_of timestamp with time zone,
    tax_source character varying,
    subtotal_cents integer DEFAULT 0 NOT NULL,
    total_cents integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    unit_cost_cents bigint,
    cost_source character varying,
    customer_visible boolean DEFAULT true NOT NULL,
    parent_line_id uuid,
    display_order integer DEFAULT 0 NOT NULL,
    is_section_header boolean DEFAULT false NOT NULL,
    CONSTRAINT chk_section_header_no_parent CHECK ((NOT ((is_section_header = true) AND (parent_line_id IS NOT NULL))))
);


--
-- Name: quote_line_tax_component; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_line_tax_component (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    quote_line_id uuid NOT NULL,
    tax_rate_version_id bigint NOT NULL,
    component_code character varying NOT NULL,
    rate_pct numeric(7,4) NOT NULL,
    amount_cents integer NOT NULL,
    tenant_id uuid NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: quote_link_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_link_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: quote_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_message (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    quote_id uuid NOT NULL,
    contact_id uuid,
    action_type character varying NOT NULL,
    message character varying NOT NULL,
    attachments jsonb,
    CONSTRAINT quote_message_action_type_chk CHECK (((action_type)::text = ANY ((ARRAY['contact'::character varying, 'tenant_user'::character varying, 'system'::character varying])::text[])))
);


--
-- Name: quote_pending_edit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_pending_edit (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    quote_id uuid NOT NULL,
    quote_version_id uuid NOT NULL,
    editor_user_id uuid NOT NULL,
    edit_type text NOT NULL,
    target_line_id uuid,
    edit_payload jsonb NOT NULL,
    annotation text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT chk_quote_pending_edit_type CHECK ((edit_type = ANY (ARRAY['modify_line'::text, 'add_line'::text, 'delete_line'::text, 'edit_notes'::text])))
);


--
-- Name: quote_public_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_public_link (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    quote_id uuid NOT NULL,
    contact_id uuid NOT NULL,
    token_hash character varying NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '90 days'::interval) NOT NULL,
    max_uses integer DEFAULT 1 NOT NULL,
    used_count integer DEFAULT 0 NOT NULL,
    permissions jsonb,
    status_id uuid NOT NULL,
    last_used_at timestamp with time zone,
    tenant_id uuid NOT NULL,
    signed_token text DEFAULT 'legacy.placeholder'::text NOT NULL,
    revoked_at timestamp with time zone,
    created_by_user_id uuid
);


--
-- Name: quote_public_link_contact_action; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_public_link_contact_action (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    quote_id uuid NOT NULL,
    quote_version_id uuid,
    contact_id uuid NOT NULL,
    qpl_contact_action_type_id uuid NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    ip inet,
    user_agent character varying,
    payload jsonb,
    tenant_id uuid NOT NULL
);


--
-- Name: quote_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_terminal boolean DEFAULT false NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: quote_template; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_template (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid,
    name text NOT NULL,
    description text,
    style text NOT NULL,
    category text,
    system_template_id uuid,
    forked_from_version integer,
    current_version integer DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_system_template boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT chk_quote_template_style CHECK ((style = ANY (ARRAY['component'::text, 'deliverable'::text, 'lump_sum'::text])))
);


--
-- Name: quote_template_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_template_line (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid,
    quote_template_id uuid NOT NULL,
    parent_line_id uuid,
    display_order integer DEFAULT 0 NOT NULL,
    qco_line_type_id uuid NOT NULL,
    description text NOT NULL,
    default_quantity numeric(12,3) DEFAULT 1 NOT NULL,
    default_unit_price_cents integer DEFAULT 0 NOT NULL,
    customer_visible boolean DEFAULT true NOT NULL,
    is_section_header boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: quote_template_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_template_version (
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    template_id uuid NOT NULL,
    version_no integer NOT NULL,
    content_json jsonb NOT NULL,
    changelog text
);


--
-- Name: quote_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quote_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id uuid NOT NULL,
    quote_id uuid NOT NULL,
    version_no integer NOT NULL,
    snapshot jsonb NOT NULL,
    pdf_object_key character varying,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid NOT NULL,
    presentation_style character varying DEFAULT 'clean'::character varying NOT NULL,
    CONSTRAINT quote_version_presentation_style_chk CHECK (((presentation_style)::text = ANY ((ARRAY['clean'::character varying, 'line_itemed'::character varying, 'hybrid'::character varying])::text[])))
);


--
-- Name: site; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.site (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    name character varying,
    notes character varying,
    is_active boolean DEFAULT true NOT NULL,
    lifecycle_status_id uuid,
    jurisdiction_code character varying,
    gate_code character varying(50),
    access_instructions text,
    hazard_notes text,
    site_type text DEFAULT 'residential'::text NOT NULL,
    CONSTRAINT site_type_chk CHECK ((site_type = ANY (ARRAY['commercial'::text, 'residential'::text, 'industrial'::text])))
);


--
-- Name: site_lifecycle_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.site_lifecycle_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: sms_quota_period; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sms_quota_period (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    included_segments integer DEFAULT 100 NOT NULL,
    used_segments integer DEFAULT 0 NOT NULL,
    overage_segments integer GENERATED ALWAYS AS (GREATEST(0, (used_segments - included_segments))) STORED,
    cap_policy text DEFAULT 'soft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT sms_quota_period_cap_policy_chk CHECK ((cap_policy = ANY (ARRAY['soft'::text, 'hard'::text])))
);


--
-- Name: sso_provider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sso_provider (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: stripe_webhook_event_processed; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stripe_webhook_event_processed (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    event_id text NOT NULL,
    processed_at timestamp with time zone NOT NULL,
    event_type text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    product_plan_code character varying NOT NULL,
    status_id uuid NOT NULL,
    quantity_seats integer DEFAULT 1 NOT NULL,
    billing_anchor date,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    canceled_at timestamp with time zone,
    psp_provider character varying,
    psp_subscription_id character varying,
    psp_customer_id character varying,
    billing_interval character varying DEFAULT 'monthly'::character varying NOT NULL,
    trial_ends_at timestamp with time zone,
    renews_at timestamp with time zone,
    cancel_at_period_end boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    stripe_schedule_id text,
    CONSTRAINT subscription_billing_interval_chk CHECK (((billing_interval)::text = ANY ((ARRAY['monthly'::character varying, 'annual'::character varying])::text[])))
);


--
-- Name: subscription_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_billing_active boolean DEFAULT true NOT NULL
);


--
-- Name: subscription_tier; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_tier (
    tier_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tier_name text NOT NULL,
    display_label text NOT NULL,
    annual_price_cents integer NOT NULL,
    is_trial boolean DEFAULT false NOT NULL,
    trial_duration_days integer,
    is_active boolean DEFAULT true NOT NULL,
    display_order integer NOT NULL,
    stripe_price_id_monthly text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    product_plan_code character varying,
    schedule_lanes integer DEFAULT 0 NOT NULL,
    monthly_price_cents integer NOT NULL,
    stripe_price_id_annual text,
    free_period_days integer,
    requires_payment_method boolean DEFAULT true NOT NULL,
    signup_cap integer,
    price_locked boolean DEFAULT false NOT NULL
);


--
-- Name: subscription_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_usage (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id bigint NOT NULL,
    subscription_id uuid NOT NULL,
    product_feature_code character varying NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    used_quantity integer DEFAULT 0 NOT NULL,
    tenant_id uuid NOT NULL
);


--
-- Name: subscription_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subscription_usage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subscription_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subscription_usage_id_seq OWNED BY public.subscription_usage.id;


--
-- Name: supplier; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    name character varying NOT NULL,
    website character varying,
    api_auth_type character varying,
    api_base_url character varying,
    is_active boolean DEFAULT true NOT NULL,
    lifecycle_status_id uuid
);


--
-- Name: supplier_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_item (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    supplier_id uuid NOT NULL,
    sku character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    uom_id uuid NOT NULL,
    category_id uuid,
    taxability_code character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: supplier_item_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_item_category (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: supplier_item_price; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_item_price (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    tenant_id uuid,
    supplier_item_id uuid NOT NULL,
    unit_price numeric(19,4) NOT NULL,
    currency character varying(3) DEFAULT 'USD'::character varying NOT NULL,
    valid_period tstzrange DEFAULT tstzrange(now(), NULL::timestamp with time zone, '[)'::text) NOT NULL,
    CONSTRAINT sip_valid_period_chk CHECK ((NOT isempty(valid_period)))
);


--
-- Name: supplier_item_price_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supplier_item_price_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supplier_item_price_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.supplier_item_price_id_seq OWNED BY public.supplier_item_price.id;


--
-- Name: supplier_item_uom; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_item_uom (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: supplier_lifecycle_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_lifecycle_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: sync_conflict_classification_matrix; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_conflict_classification_matrix (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    operation_type text NOT NULL,
    trigger_condition text NOT NULL,
    severity text NOT NULL,
    classification_reason text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    tenant_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT chk_sync_conflict_matrix_severity CHECK ((severity = ANY (ARRAY['auto_silent'::text, 'auto_notice'::text, 'tech_resolvable'::text, 'owner_escalation'::text])))
);


--
-- Name: tax_rate_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tax_rate_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    jurisdiction_code character varying NOT NULL,
    description character varying,
    rate_pct numeric(7,4) NOT NULL,
    valid_period tstzrange NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    external_tax_agency_id character varying(100),
    taxability_code character varying DEFAULT 'taxable'::character varying NOT NULL,
    CONSTRAINT tax_rate_version_valid_period_chk CHECK ((NOT isempty(valid_period)))
);


--
-- Name: tax_rate_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tax_rate_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tax_rate_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tax_rate_version_id_seq OWNED BY public.tax_rate_version.id;


--
-- Name: taxability_code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.taxability_code (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying,
    description character varying,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: tech_availability; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tech_availability (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    availability_type text NOT NULL,
    starts_at timestamp with time zone,
    ends_at timestamp with time zone,
    recurrence_rrule text,
    notes text,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_availability_shape CHECK ((((availability_type = 'working_hours'::text) AND (recurrence_rrule IS NOT NULL)) OR ((availability_type = ANY (ARRAY['pto'::text, 'unavailable'::text])) AND (starts_at IS NOT NULL) AND (ends_at IS NOT NULL) AND (ends_at > starts_at)))),
    CONSTRAINT ck_availability_type CHECK ((availability_type = ANY (ARRAY['working_hours'::text, 'pto'::text, 'unavailable'::text])))
);


--
-- Name: tenant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    current_subscription_tier_id uuid NOT NULL,
    trial_started_at timestamp with time zone,
    trial_ends_at timestamp with time zone,
    trial_length_days_override integer,
    stripe_customer_id text,
    mfa_grace_period_started_at timestamp with time zone,
    stripe_connect_account_id text,
    free_period_ends_at timestamp with time zone,
    charter_member_number integer,
    charter_eligible boolean DEFAULT true NOT NULL,
    stripe_connect_charges_enabled boolean,
    stripe_connect_payouts_enabled boolean,
    billing_contact_phone text,
    billing_contact_email text
);


--
-- Name: tenant_10dlc_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_10dlc_profile (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    tenant_id uuid NOT NULL,
    legal_business_name text NOT NULL,
    dba_name text,
    ein text,
    hq_address_line1 text,
    hq_address_line2 text,
    hq_city text,
    hq_state text,
    hq_postal_code text,
    hq_country text DEFAULT 'US'::text NOT NULL,
    support_email text,
    support_phone text,
    website text,
    stock_symbol text,
    vertical text,
    requirements_emailed_at timestamp with time zone
);


--
-- Name: tenant_calendar_integration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_calendar_integration (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    provider_code text NOT NULL,
    external_calendar_id text NOT NULL,
    access_token_encrypted bytea NOT NULL,
    refresh_token_encrypted bytea NOT NULL,
    token_expires_at timestamp with time zone NOT NULL,
    sync_status text DEFAULT 'active'::text NOT NULL,
    last_sync_at timestamp with time zone,
    last_sync_cursor text,
    connected_by_user_id uuid NOT NULL,
    connected_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_provider_code CHECK ((provider_code = ANY (ARRAY['google'::text, 'outlook'::text]))),
    CONSTRAINT ck_sync_status CHECK ((sync_status = ANY (ARRAY['active'::text, 'paused'::text, 'error'::text])))
);


--
-- Name: tenant_domain; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_domain (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    domain public.citext NOT NULL,
    verified_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: tenant_email_branding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_email_branding (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    tenant_id uuid NOT NULL,
    logo_s3_path text,
    brand_color_hex character varying(7),
    email_signature text,
    custom_footer text
);


--
-- Name: tenant_legal_acceptance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_legal_acceptance (
    acceptance_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    document_type text NOT NULL,
    document_version_hash text NOT NULL,
    accepted_at timestamp with time zone NOT NULL,
    ip_address inet NOT NULL,
    user_agent text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    CONSTRAINT tenant_legal_acceptance_document_type_chk CHECK ((document_type = ANY (ARRAY['tos'::text, 'privacy'::text, 'eula'::text, 'marketing_email_optin'::text])))
);


--
-- Name: tenant_markup_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_markup_version (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    job_expense_category_code character varying NOT NULL,
    markup_pct numeric(7,4) NOT NULL,
    markup_amt_cents integer,
    valid_period tstzrange DEFAULT tstzrange(now(), NULL::timestamp with time zone, '[)'::text) NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tmv_markup_presence_chk CHECK (((markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL))),
    CONSTRAINT tmv_valid_period_chk CHECK ((NOT isempty(valid_period)))
);


--
-- Name: tenant_markup_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tenant_markup_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tenant_markup_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tenant_markup_version_id_seq OWNED BY public.tenant_markup_version.id;


--
-- Name: tenant_messaging_registration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_messaging_registration (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    entity_type text NOT NULL,
    status text NOT NULL,
    telnyx_brand_id text,
    telnyx_campaign_id text,
    telnyx_phone_number text,
    quoted_setup_cents integer,
    quoted_monthly_cents integer,
    stripe_checkout_id text,
    stripe_payment_intent text,
    otp_requested_at timestamp with time zone,
    otp_verified_at timestamp with time zone,
    failure_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    stripe_recurring_item_id text,
    recurring_item_created_at timestamp with time zone
);


--
-- Name: tenant_onboarding_checklist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_onboarding_checklist (
    tenant_id uuid NOT NULL,
    account_created boolean DEFAULT false NOT NULL,
    legal_accepted boolean DEFAULT false NOT NULL,
    tier_selected boolean DEFAULT false NOT NULL,
    first_customer_added boolean DEFAULT false NOT NULL,
    first_customer_added_at timestamp with time zone,
    catalog_setup boolean DEFAULT false NOT NULL,
    catalog_setup_at timestamp with time zone,
    quickbooks_connected boolean DEFAULT false NOT NULL,
    quickbooks_skipped boolean DEFAULT false NOT NULL,
    calendar_connected boolean DEFAULT false NOT NULL,
    calendar_skipped boolean DEFAULT false NOT NULL,
    team_invited boolean DEFAULT false NOT NULL,
    team_skipped boolean DEFAULT false NOT NULL,
    checklist_hidden boolean DEFAULT false NOT NULL,
    checklist_dismissed_permanently boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    messaging_setup boolean DEFAULT false NOT NULL
);


--
-- Name: tenant_phone_number; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_phone_number (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    phone_number text NOT NULL,
    area_code text NOT NULL,
    carrier text DEFAULT 'telnyx'::text NOT NULL,
    carrier_provisioning_id text,
    monthly_fee_cents integer DEFAULT 100 NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    provisioned_at timestamp with time zone,
    released_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT tenant_phone_number_carrier_chk CHECK ((carrier = 'telnyx'::text)),
    CONSTRAINT tenant_phone_number_status_chk CHECK ((status = ANY (ARRAY['active'::text, 'released'::text, 'provisioning_failed'::text])))
);


--
-- Name: tenant_product_feature_override; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_product_feature_override (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    tenant_id uuid NOT NULL,
    product_feature_code character varying NOT NULL,
    limit_quantity integer,
    included_quantity integer,
    overage_price_cents integer,
    overage_cap_per_period integer,
    alert_threshold_pct integer,
    enabled boolean DEFAULT true NOT NULL
);


--
-- Name: tenant_signup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_signup (
    tenant_id uuid NOT NULL,
    signup_state text DEFAULT 'step1_account'::text NOT NULL,
    signup_started_at timestamp with time zone NOT NULL,
    signup_completed_at timestamp with time zone,
    business_name text NOT NULL,
    trade text NOT NULL,
    business_size text NOT NULL,
    zip text NOT NULL,
    time_zone text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    owner_email text,
    owner_first_name text,
    owner_last_name text,
    CONSTRAINT tenant_signup_state_chk CHECK ((signup_state = ANY (ARRAY['step1_account'::text, 'step2_legal'::text, 'step3_phone'::text, 'step4_tier'::text, 'step5_confirm'::text, 'complete'::text])))
);


--
-- Name: tenant_site; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_site (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    slug character varying(63) NOT NULL,
    site_kind character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    display_name character varying(200) NOT NULL,
    tagline character varying(300),
    public_email character varying(320),
    public_phone character varying(32),
    public_city character varying(120),
    public_state character varying(2),
    public_address_line1 character varying(200),
    public_postal_code character varying(10),
    show_full_address boolean DEFAULT false NOT NULL,
    template_version character varying(20) DEFAULT 'v1'::character varying NOT NULL,
    published_snapshot jsonb,
    published_at timestamp with time zone,
    unpublished_at timestamp with time zone,
    kit_sent_at timestamp with time zone,
    website_auto_populated boolean DEFAULT false NOT NULL,
    idempotency_key character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT ck_tenant_site_kind CHECK (((site_kind)::text = ANY ((ARRAY['compliance_kit'::character varying, 'hosted_compliance'::character varying])::text[]))),
    CONSTRAINT ck_tenant_site_slug_format CHECK (((slug)::text ~ '^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$'::text)),
    CONSTRAINT ck_tenant_site_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'unpublished'::character varying])::text[])))
);


--
-- Name: tenant_subscription_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_subscription_usage (
    tenant_id uuid NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    current_user_count integer DEFAULT 0 NOT NULL,
    current_sms_segment_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: tenant_tier_override; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_tier_override (
    tenant_id uuid NOT NULL,
    override_tier_id uuid,
    override_trial_length_days integer,
    override_reason text NOT NULL,
    set_by_operator_user_id uuid NOT NULL,
    set_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    override_free_period_ends_at timestamp with time zone
);


--
-- Name: tenant_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_user (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role_code character varying NOT NULL,
    status_id uuid NOT NULL,
    invited_at timestamp with time zone,
    joined_at timestamp with time zone,
    suspended_at timestamp with time zone,
    suspended_by uuid,
    is_active boolean DEFAULT true NOT NULL,
    skill_level_code character varying,
    employee_number character varying
);


--
-- Name: tenant_user_invite; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_user_invite (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    email public.citext NOT NULL,
    token_hash character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    invited_by uuid,
    is_active boolean DEFAULT true NOT NULL,
    role_code character varying,
    CONSTRAINT tenant_user_invite_email_format_chk CHECK ((email OPERATOR(public.~*) '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::public.citext))
);


--
-- Name: tenant_user_role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_user_role (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    description character varying,
    permissions jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: tenant_user_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_user_status (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    tenant_id uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: usage_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usage_ledger (
    created_at timestamp with time zone NOT NULL,
    created_by uuid,
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    subscription_id uuid,
    product_feature_code character varying NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    quantity numeric(12,4) DEFAULT 1 NOT NULL,
    entity_type_code character varying,
    entity_id uuid,
    idempotency_key character varying NOT NULL,
    is_reported boolean DEFAULT false NOT NULL,
    reported_at timestamp with time zone,
    contextdata jsonb
);


--
-- Name: usage_ledger_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usage_ledger_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usage_ledger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usage_ledger_id_seq OWNED BY public.usage_ledger.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    email public.citext NOT NULL,
    first_name character varying,
    last_name character varying,
    is_platform_user boolean DEFAULT false NOT NULL,
    platform_role_code character varying,
    password_hash character varying,
    email_verified_at timestamp with time zone,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    password_updated_at timestamp with time zone,
    require_password_reset boolean DEFAULT false NOT NULL,
    mfa_enforced boolean DEFAULT false NOT NULL,
    preferred_mfa_channel text DEFAULT 'email'::text,
    totp_secret character varying,
    is_active boolean DEFAULT true NOT NULL,
    last_login_at timestamp with time zone,
    display_color character varying(7),
    phone_number character varying,
    time_zone character varying DEFAULT 'America/New_York'::character varying,
    profile_photo_s3_key text,
    language_preference character varying DEFAULT 'en'::character varying,
    CONSTRAINT user_email_format_chk CHECK ((email OPERATOR(public.~*) '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::public.citext)),
    CONSTRAINT user_language_preference_chk CHECK (((language_preference IS NULL) OR ((language_preference)::text = 'en'::text))),
    CONSTRAINT user_platform_mfa_required_chk CHECK (((is_platform_user = false) OR (mfa_enforced = true))),
    CONSTRAINT user_platform_role_chk CHECK ((((is_platform_user = true) AND (platform_role_code IS NOT NULL)) OR ((is_platform_user = false) AND (platform_role_code IS NULL)))),
    CONSTRAINT user_preferred_mfa_channel_chk CHECK (((preferred_mfa_channel IS NULL) OR (preferred_mfa_channel = ANY (ARRAY['email'::text, 'sms'::text, 'totp'::text]))))
);


--
-- Name: user_dashboard_widget; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_dashboard_widget (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    widget_type character varying(64) NOT NULL,
    widget_config_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    position_x integer DEFAULT 0 NOT NULL,
    position_y integer DEFAULT 0 NOT NULL,
    width integer DEFAULT 2 NOT NULL,
    height integer DEFAULT 2 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT ck_widget_height CHECK (((height >= 1) AND (height <= 8))),
    CONSTRAINT ck_widget_position_x CHECK ((position_x >= 0)),
    CONSTRAINT ck_widget_position_y CHECK ((position_y >= 0)),
    CONSTRAINT ck_widget_width CHECK (((width >= 1) AND (width <= 12)))
);


--
-- Name: user_endpoint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_endpoint (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    channel character varying NOT NULL,
    value character varying NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    verification_status character varying DEFAULT 'pending'::character varying NOT NULL,
    verified_at timestamp with time zone,
    consent_status character varying DEFAULT 'unknown'::character varying NOT NULL,
    consent_updated_at timestamp with time zone,
    contextdata jsonb,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT user_endpoint_channel_chk CHECK (((channel)::text = ANY (ARRAY['email'::text, 'sms'::text, 'in_app'::text, 'push'::text]))),
    CONSTRAINT user_endpoint_consent_status_chk CHECK (((consent_status)::text = ANY ((ARRAY['unknown'::character varying, 'opted_in'::character varying, 'opted_out'::character varying])::text[]))),
    CONSTRAINT user_endpoint_email_format_chk CHECK ((((channel)::text <> 'email'::text) OR ((value)::text ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text))),
    CONSTRAINT user_endpoint_verification_status_chk CHECK (((verification_status)::text = ANY ((ARRAY['pending'::character varying, 'verified'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: user_mfa_method; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_mfa_method (
    mfa_method_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    method_type text NOT NULL,
    enrolled_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone,
    cognito_method_id text NOT NULL,
    verification_status text DEFAULT 'verified'::text NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: user_mfa_recovery_code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_mfa_recovery_code (
    code_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    code_hash text NOT NULL,
    generated_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    set_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by uuid
);


--
-- Name: user_preference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_preference (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    tenant_id uuid,
    preferences jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: user_session_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_session_history (
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    first_login_at timestamp with time zone NOT NULL,
    total_session_count integer DEFAULT 0 NOT NULL,
    last_login_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: user_session_metadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_session_metadata (
    session_id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    device_fingerprint text NOT NULL,
    display_label text NOT NULL,
    ip_address inet NOT NULL,
    geolocation text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_active_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: user_setting_override; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_setting_override (
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    setting_key text NOT NULL,
    value jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: user_sms_consent_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sms_consent_audit (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    user_endpoint_id uuid,
    action text NOT NULL,
    consent_text_hash text NOT NULL,
    ip_address text,
    attested_at timestamp with time zone NOT NULL,
    created_by uuid,
    CONSTRAINT user_sms_consent_audit_action_chk CHECK ((action = ANY (ARRAY['attested'::text, 'double_opt_in_sent'::text, 'double_opt_in_confirmed'::text, 'opted_out'::text])))
);


--
-- Name: user_sso_identity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sso_identity (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    sso_provider_code character varying NOT NULL,
    provider_user_id character varying NOT NULL,
    provider_metadata jsonb
);


--
-- Name: voice_command_entity_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voice_command_entity_link (
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    voice_command_log_id bigint NOT NULL,
    entity_type character varying NOT NULL,
    entity_id uuid NOT NULL,
    action character varying,
    created_at timestamp with time zone NOT NULL,
    created_by uuid
);


--
-- Name: voice_command_entity_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.voice_command_entity_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: voice_command_entity_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.voice_command_entity_link_id_seq OWNED BY public.voice_command_entity_link.id;


--
-- Name: voice_command_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voice_command_log (
    id bigint NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    message_id uuid,
    intent_detected character varying,
    entities_extracted jsonb,
    action_executed character varying,
    whisper_latency_ms integer,
    ollama_latency_ms integer,
    total_latency_ms integer,
    is_successful boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    audio_object_key text,
    captured_at timestamp with time zone,
    uploaded_at timestamp with time zone,
    transcribed_at timestamp with time zone,
    parsed_at timestamp with time zone,
    processing_status text,
    idempotency_uuid uuid,
    CONSTRAINT chk_voice_command_log_processing_status CHECK (((processing_status IS NULL) OR (processing_status = ANY (ARRAY['pending_upload'::text, 'uploading'::text, 'transcribing'::text, 'parsing'::text, 'completed'::text, 'failed'::text]))))
);


--
-- Name: voice_command_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.voice_command_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: voice_command_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.voice_command_log_id_seq OWNED BY public.voice_command_log.id;


--
-- Name: voice_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voice_feedback (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    voice_command_log_id bigint,
    original_transcription text NOT NULL,
    corrected_text text,
    intent_misparsed boolean DEFAULT false NOT NULL,
    corrected_intent text,
    feedback_notes text,
    s3_export_key text,
    exported_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


--
-- Name: webhook_delivery_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_delivery_attempt (
    created_at timestamp with time zone NOT NULL,
    id bigint NOT NULL,
    webhook_event_id uuid NOT NULL,
    webhook_endpoint_id uuid NOT NULL,
    attempt_no integer DEFAULT 1 NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    http_status integer,
    error character varying,
    request_header jsonb,
    response_body jsonb,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    next_attempt_after timestamp with time zone,
    tenant_id uuid NOT NULL,
    CONSTRAINT webhook_delivery_attempt_status_chk CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'success'::character varying, 'failed'::character varying, 'giving_up'::character varying])::text[])))
);


--
-- Name: webhook_delivery_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.webhook_delivery_attempt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webhook_delivery_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.webhook_delivery_attempt_id_seq OWNED BY public.webhook_delivery_attempt.id;


--
-- Name: webhook_endpoint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_endpoint (
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    url character varying NOT NULL,
    event_filter character varying[],
    secret character varying,
    enabled boolean DEFAULT true NOT NULL,
    disabled_at timestamp with time zone
);


--
-- Name: webhook_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_event (
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    tenant_id uuid,
    event_type_code character varying,
    entity_type_code character varying,
    entity_id uuid,
    payload jsonb NOT NULL,
    source_app character varying,
    event_type character varying,
    event_id character varying,
    signature_valid boolean DEFAULT false NOT NULL,
    processed_at timestamp with time zone,
    error_message character varying
);


--
-- Name: webhook_event_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_event_type (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by uuid,
    updated_by uuid,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: event id; Type: DEFAULT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.event ALTER COLUMN id SET DEFAULT nextval('audit.event_id_seq'::regclass);


--
-- Name: auth_password_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_history ALTER COLUMN id SET DEFAULT nextval('public.auth_password_history_id_seq'::regclass);


--
-- Name: connector_run_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_run_log ALTER COLUMN id SET DEFAULT nextval('public.connector_run_log_id_seq'::regclass);


--
-- Name: discount_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_version ALTER COLUMN id SET DEFAULT nextval('public.discount_version_id_seq'::regclass);


--
-- Name: integration_sync_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_log ALTER COLUMN id SET DEFAULT nextval('public.integration_sync_log_id_seq'::regclass);


--
-- Name: notification_delivery_attempt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_delivery_attempt ALTER COLUMN id SET DEFAULT nextval('public.notification_delivery_attempt_id_seq'::regclass);


--
-- Name: pricebook_item_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item_version ALTER COLUMN id SET DEFAULT nextval('public.pricebook_item_version_id_seq'::regclass);


--
-- Name: pricing_cache id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache ALTER COLUMN id SET DEFAULT nextval('public.pricing_cache_id_seq'::regclass);


--
-- Name: product_plan_product_feature_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_product_feature_version ALTER COLUMN id SET DEFAULT nextval('public.product_plan_product_feature_version_id_seq'::regclass);


--
-- Name: product_plan_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_version ALTER COLUMN id SET DEFAULT nextval('public.product_plan_version_id_seq'::regclass);


--
-- Name: psp_transaction_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_transaction_log ALTER COLUMN id SET DEFAULT nextval('public.psp_transaction_log_id_seq'::regclass);


--
-- Name: subscription_usage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage ALTER COLUMN id SET DEFAULT nextval('public.subscription_usage_id_seq'::regclass);


--
-- Name: supplier_item_price id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price ALTER COLUMN id SET DEFAULT nextval('public.supplier_item_price_id_seq'::regclass);


--
-- Name: tax_rate_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tax_rate_version ALTER COLUMN id SET DEFAULT nextval('public.tax_rate_version_id_seq'::regclass);


--
-- Name: tenant_markup_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_markup_version ALTER COLUMN id SET DEFAULT nextval('public.tenant_markup_version_id_seq'::regclass);


--
-- Name: usage_ledger id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger ALTER COLUMN id SET DEFAULT nextval('public.usage_ledger_id_seq'::regclass);


--
-- Name: voice_command_entity_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_entity_link ALTER COLUMN id SET DEFAULT nextval('public.voice_command_entity_link_id_seq'::regclass);


--
-- Name: voice_command_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_log ALTER COLUMN id SET DEFAULT nextval('public.voice_command_log_id_seq'::regclass);


--
-- Name: webhook_delivery_attempt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_delivery_attempt ALTER COLUMN id SET DEFAULT nextval('public.webhook_delivery_attempt_id_seq'::regclass);


--
-- Name: event event_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.event
    ADD CONSTRAINT event_pkey PRIMARY KEY (id);


--
-- Name: address address_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address
    ADD CONSTRAINT address_pkey PRIMARY KEY (id);


--
-- Name: address_type address_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_type
    ADD CONSTRAINT address_type_pkey PRIMARY KEY (code);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: app_service_category app_service_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service_category
    ADD CONSTRAINT app_service_category_pkey PRIMARY KEY (code);


--
-- Name: app_service app_service_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service
    ADD CONSTRAINT app_service_pkey PRIMARY KEY (id);


--
-- Name: app_service_provider app_service_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service_provider
    ADD CONSTRAINT app_service_provider_pkey PRIMARY KEY (code);


--
-- Name: auth_api_token auth_api_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_api_token
    ADD CONSTRAINT auth_api_token_pkey PRIMARY KEY (id);


--
-- Name: auth_email_verification auth_email_verification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_email_verification
    ADD CONSTRAINT auth_email_verification_pkey PRIMARY KEY (id);


--
-- Name: auth_jwk auth_jwk_kid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_jwk
    ADD CONSTRAINT auth_jwk_kid_key UNIQUE (kid);


--
-- Name: auth_jwk auth_jwk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_jwk
    ADD CONSTRAINT auth_jwk_pkey PRIMARY KEY (id);


--
-- Name: auth_mfa_otp auth_mfa_otp_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_mfa_otp
    ADD CONSTRAINT auth_mfa_otp_pkey PRIMARY KEY (id);


--
-- Name: auth_password_history auth_password_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_history
    ADD CONSTRAINT auth_password_history_pkey PRIMARY KEY (id);


--
-- Name: auth_password_reset auth_password_reset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_reset
    ADD CONSTRAINT auth_password_reset_pkey PRIMARY KEY (id);


--
-- Name: auth_refresh_token auth_refresh_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_token
    ADD CONSTRAINT auth_refresh_token_pkey PRIMARY KEY (id);


--
-- Name: change_order_attachment change_order_attachment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_attachment
    ADD CONSTRAINT change_order_attachment_pkey PRIMARY KEY (id);


--
-- Name: change_order_line change_order_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_pkey PRIMARY KEY (id);


--
-- Name: change_order_line_tax_component change_order_line_tax_component_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line_tax_component
    ADD CONSTRAINT change_order_line_tax_component_pkey PRIMARY KEY (id);


--
-- Name: change_order change_order_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order
    ADD CONSTRAINT change_order_pkey PRIMARY KEY (id);


--
-- Name: communication_template communication_template_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_template
    ADD CONSTRAINT communication_template_pkey PRIMARY KEY (id);


--
-- Name: connector_config connector_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_config
    ADD CONSTRAINT connector_config_pkey PRIMARY KEY (id);


--
-- Name: connector_config connector_config_supplier_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_config
    ADD CONSTRAINT connector_config_supplier_id_key UNIQUE (supplier_id);


--
-- Name: connector_run_log connector_run_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_run_log
    ADD CONSTRAINT connector_run_log_pkey PRIMARY KEY (id);


--
-- Name: contact_endpoint contact_endpoint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_endpoint
    ADD CONSTRAINT contact_endpoint_pkey PRIMARY KEY (id);


--
-- Name: contact contact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact
    ADD CONSTRAINT contact_pkey PRIMARY KEY (id);


--
-- Name: contact_portal_invite contact_portal_invite_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_portal_invite
    ADD CONSTRAINT contact_portal_invite_pkey PRIMARY KEY (id);


--
-- Name: contact_type contact_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_type
    ADD CONSTRAINT contact_type_pkey PRIMARY KEY (code);


--
-- Name: conversation_message conversation_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message
    ADD CONSTRAINT conversation_message_pkey PRIMARY KEY (id);


--
-- Name: conversation_session conversation_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_session
    ADD CONSTRAINT conversation_session_pkey PRIMARY KEY (id);


--
-- Name: currency currency_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency
    ADD CONSTRAINT currency_pkey PRIMARY KEY (code);


--
-- Name: customer_comm_template_type customer_comm_template_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_comm_template_type
    ADD CONSTRAINT customer_comm_template_type_pkey PRIMARY KEY (code);


--
-- Name: customer_communication_message customer_communication_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message
    ADD CONSTRAINT customer_communication_message_pkey PRIMARY KEY (id);


--
-- Name: customer_communication_message_read_state customer_communication_message_read_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message_read_state
    ADD CONSTRAINT customer_communication_message_read_state_pkey PRIMARY KEY (message_id, user_id);


--
-- Name: customer_communication customer_communication_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_pkey PRIMARY KEY (id);


--
-- Name: customer_communication_thread customer_communication_thread_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_pkey PRIMARY KEY (id);


--
-- Name: customer_communication_unrouted customer_communication_unrouted_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_unrouted
    ADD CONSTRAINT customer_communication_unrouted_pkey PRIMARY KEY (id);


--
-- Name: customer_lifecycle_status customer_lifecycle_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_lifecycle_status
    ADD CONSTRAINT customer_lifecycle_status_pkey PRIMARY KEY (id);


--
-- Name: customer customer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT customer_pkey PRIMARY KEY (id);


--
-- Name: customer_sms_consent_audit customer_sms_consent_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sms_consent_audit
    ADD CONSTRAINT customer_sms_consent_audit_pkey PRIMARY KEY (id);


--
-- Name: data_export_request data_export_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_export_request
    ADD CONSTRAINT data_export_request_pkey PRIMARY KEY (export_id);


--
-- Name: discount_version discount_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_version
    ADD CONSTRAINT discount_version_pkey PRIMARY KEY (id);


--
-- Name: entity_address entity_address_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT entity_address_pkey PRIMARY KEY (id);


--
-- Name: entity_contact entity_contact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT entity_contact_pkey PRIMARY KEY (id);


--
-- Name: entity_type entity_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type
    ADD CONSTRAINT entity_type_pkey PRIMARY KEY (code);


--
-- Name: supplier_item_price exclude_supplier_item_price_period_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price
    ADD CONSTRAINT exclude_supplier_item_price_period_overlap EXCLUDE USING gist (supplier_item_id WITH =, COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =, valid_period WITH &&);


--
-- Name: idempotency_key idempotency_key_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_key
    ADD CONSTRAINT idempotency_key_pkey PRIMARY KEY (key);


--
-- Name: integration_credential integration_credential_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credential
    ADD CONSTRAINT integration_credential_pkey PRIMARY KEY (id);


--
-- Name: integration_sync_conflict integration_sync_conflict_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT integration_sync_conflict_pkey PRIMARY KEY (id);


--
-- Name: integration_sync_log integration_sync_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_log
    ADD CONSTRAINT integration_sync_log_pkey PRIMARY KEY (id);


--
-- Name: integration_sync_mapping integration_sync_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT integration_sync_mapping_pkey PRIMARY KEY (id);


--
-- Name: invoice_line invoice_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT invoice_line_pkey PRIMARY KEY (id);


--
-- Name: invoice_line_tax_component invoice_line_tax_component_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_tax_component
    ADD CONSTRAINT invoice_line_tax_component_pkey PRIMARY KEY (id);


--
-- Name: invoice invoice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_pkey PRIMARY KEY (id);


--
-- Name: invoice_public_link invoice_public_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT invoice_public_link_pkey PRIMARY KEY (id);


--
-- Name: invoice_signoff invoice_signoff_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_signoff
    ADD CONSTRAINT invoice_signoff_pkey PRIMARY KEY (id);


--
-- Name: invoice_status invoice_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_status
    ADD CONSTRAINT invoice_status_pkey PRIMARY KEY (id);


--
-- Name: job_attachment job_attachment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_attachment
    ADD CONSTRAINT job_attachment_pkey PRIMARY KEY (id);


--
-- Name: job_expense_category job_expense_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense_category
    ADD CONSTRAINT job_expense_category_pkey PRIMARY KEY (code);


--
-- Name: job_expense job_expense_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT job_expense_pkey PRIMARY KEY (id);


--
-- Name: job_notes job_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_notes
    ADD CONSTRAINT job_notes_pkey PRIMARY KEY (id);


--
-- Name: job job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_pkey PRIMARY KEY (id);


--
-- Name: job_recurrence_rule job_recurrence_rule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_recurrence_rule
    ADD CONSTRAINT job_recurrence_rule_pkey PRIMARY KEY (id);


--
-- Name: job_status job_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_status
    ADD CONSTRAINT job_status_pkey PRIMARY KEY (id);


--
-- Name: job_time_entry job_time_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT job_time_entry_pkey PRIMARY KEY (id);


--
-- Name: job_type job_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_type
    ADD CONSTRAINT job_type_pkey PRIMARY KEY (id);


--
-- Name: jwk_status jwk_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jwk_status
    ADD CONSTRAINT jwk_status_pkey PRIMARY KEY (id);


--
-- Name: labor_rate_version labor_rate_version_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.labor_rate_version
    ADD CONSTRAINT labor_rate_version_no_overlap EXCLUDE USING gist (tenant_id WITH =, skill_level_code WITH =, valid_period WITH &&);


--
-- Name: labor_rate_version labor_rate_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.labor_rate_version
    ADD CONSTRAINT labor_rate_version_pkey PRIMARY KEY (id);


--
-- Name: loto_confirmation loto_confirmation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loto_confirmation
    ADD CONSTRAINT loto_confirmation_pkey PRIMARY KEY (id);


--
-- Name: marketing_job_application marketing_job_application_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketing_job_application
    ADD CONSTRAINT marketing_job_application_pkey PRIMARY KEY (id);


--
-- Name: mfa_grace_period_tracking mfa_grace_period_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mfa_grace_period_tracking
    ADD CONSTRAINT mfa_grace_period_tracking_pkey PRIMARY KEY (tenant_id, user_id);


--
-- Name: mobile_device_push_token mobile_device_push_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT mobile_device_push_token_pkey PRIMARY KEY (id);


--
-- Name: mobile_device_push_token mobile_device_push_token_tenant_user_device_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT mobile_device_push_token_tenant_user_device_uq UNIQUE (tenant_id, user_id, device_id);


--
-- Name: mobile_push_rate_limit mobile_push_rate_limit_device_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_rate_limit
    ADD CONSTRAINT mobile_push_rate_limit_device_uq UNIQUE (device_id);


--
-- Name: mobile_push_rate_limit mobile_push_rate_limit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_rate_limit
    ADD CONSTRAINT mobile_push_rate_limit_pkey PRIMARY KEY (id);


--
-- Name: mobile_sync_event_audit mobile_sync_event_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event_audit
    ADD CONSTRAINT mobile_sync_event_audit_pkey PRIMARY KEY (id);


--
-- Name: mobile_sync_session mobile_sync_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_session
    ADD CONSTRAINT mobile_sync_session_pkey PRIMARY KEY (id);


--
-- Name: nec_calculation_log nec_calculation_log_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: nec_calculation_log nec_calculation_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_pkey PRIMARY KEY (id);


--
-- Name: notification_channel notification_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_channel
    ADD CONSTRAINT notification_channel_pkey PRIMARY KEY (code);


--
-- Name: notification_delivery_attempt notification_delivery_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_delivery_attempt
    ADD CONSTRAINT notification_delivery_attempt_pkey PRIMARY KEY (id);


--
-- Name: notification_event notification_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_event
    ADD CONSTRAINT notification_event_pkey PRIMARY KEY (id);


--
-- Name: notification_outbox notification_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_pkey PRIMARY KEY (id);


--
-- Name: notification_template notification_template_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_template
    ADD CONSTRAINT notification_template_pkey PRIMARY KEY (id);


--
-- Name: notification_type notification_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_type
    ADD CONSTRAINT notification_type_pkey PRIMARY KEY (code);


--
-- Name: password_policy password_policy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_policy
    ADD CONSTRAINT password_policy_pkey PRIMARY KEY (id);


--
-- Name: payment_method payment_method_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT payment_method_pkey PRIMARY KEY (id);


--
-- Name: payment payment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_pkey PRIMARY KEY (id);


--
-- Name: payment_schedule_line payment_schedule_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule_line
    ADD CONSTRAINT payment_schedule_line_pkey PRIMARY KEY (id);


--
-- Name: payment_schedule payment_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_pkey PRIMARY KEY (id);


--
-- Name: payment_status payment_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_status
    ADD CONSTRAINT payment_status_pkey PRIMARY KEY (id);


--
-- Name: payment_type payment_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_type
    ADD CONSTRAINT payment_type_pkey PRIMARY KEY (id);


--
-- Name: pricebook_item_version piv_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item_version
    ADD CONSTRAINT piv_no_overlap EXCLUDE USING gist (tenant_id WITH =, pricebook_item_id WITH =, valid_period WITH &&);


--
-- Name: calendar_sync_conflict pk_calendar_sync_conflict; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT pk_calendar_sync_conflict PRIMARY KEY (id);


--
-- Name: calendar_sync_log pk_calendar_sync_log; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_log
    ADD CONSTRAINT pk_calendar_sync_log PRIMARY KEY (id);


--
-- Name: carrier_fee_schedule pk_carrier_fee_schedule; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_fee_schedule
    ADD CONSTRAINT pk_carrier_fee_schedule PRIMARY KEY (id);


--
-- Name: email_template pk_email_template; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_template
    ADD CONSTRAINT pk_email_template PRIMARY KEY (template_id);


--
-- Name: feedback_submission pk_feedback_submission; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback_submission
    ADD CONSTRAINT pk_feedback_submission PRIMARY KEY (submission_id);


--
-- Name: help_article pk_help_article; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_article
    ADD CONSTRAINT pk_help_article PRIMARY KEY (code);


--
-- Name: help_article_chunk pk_help_article_chunk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_article_chunk
    ADD CONSTRAINT pk_help_article_chunk PRIMARY KEY (chunk_id);


--
-- Name: help_chat_message pk_help_chat_message; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_chat_message
    ADD CONSTRAINT pk_help_chat_message PRIMARY KEY (message_id);


--
-- Name: help_chat_session pk_help_chat_session; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_chat_session
    ADD CONSTRAINT pk_help_chat_session PRIMARY KEY (id);


--
-- Name: help_training_corpus pk_help_training_corpus; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_training_corpus
    ADD CONSTRAINT pk_help_training_corpus PRIMARY KEY (corpus_id);


--
-- Name: in_app_notification pk_in_app_notification; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notification
    ADD CONSTRAINT pk_in_app_notification PRIMARY KEY (id);


--
-- Name: job_tech_assignment pk_job_tech_assignment; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT pk_job_tech_assignment PRIMARY KEY (id);


--
-- Name: marketing_contact_submission pk_marketing_contact_submission; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketing_contact_submission
    ADD CONSTRAINT pk_marketing_contact_submission PRIMARY KEY (id);


--
-- Name: marketing_newsletter_subscriber pk_marketing_newsletter_subscriber; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketing_newsletter_subscriber
    ADD CONSTRAINT pk_marketing_newsletter_subscriber PRIMARY KEY (id);


--
-- Name: marketing_waitlist_signup pk_marketing_waitlist_signup; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketing_waitlist_signup
    ADD CONSTRAINT pk_marketing_waitlist_signup PRIMARY KEY (id);


--
-- Name: mobile_push_permission_state pk_mobile_push_permission_state; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_permission_state
    ADD CONSTRAINT pk_mobile_push_permission_state PRIMARY KEY (tenant_id, user_id, device_id);


--
-- Name: mobile_sync_event pk_mobile_sync_event; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event
    ADD CONSTRAINT pk_mobile_sync_event PRIMARY KEY (id);


--
-- Name: mobile_sync_owner_escalation pk_mobile_sync_owner_escalation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT pk_mobile_sync_owner_escalation PRIMARY KEY (id);


--
-- Name: notification_category_sub_trigger pk_notif_sub_trigger; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category_sub_trigger
    ADD CONSTRAINT pk_notif_sub_trigger PRIMARY KEY (code);


--
-- Name: notification_category pk_notification_category; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category
    ADD CONSTRAINT pk_notification_category PRIMARY KEY (code);


--
-- Name: notification_default_policy pk_notification_default_policy; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_default_policy
    ADD CONSTRAINT pk_notification_default_policy PRIMARY KEY (id);


--
-- Name: notification_preference pk_notification_preference; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preference
    ADD CONSTRAINT pk_notification_preference PRIMARY KEY (id);


--
-- Name: public_link_short_code pk_public_link_short_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.public_link_short_code
    ADD CONSTRAINT pk_public_link_short_code PRIMARY KEY (short_code);


--
-- Name: stripe_webhook_event_processed pk_stripe_webhook_event_processed; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stripe_webhook_event_processed
    ADD CONSTRAINT pk_stripe_webhook_event_processed PRIMARY KEY (event_id);


--
-- Name: subscription_tier pk_subscription_tier; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_tier
    ADD CONSTRAINT pk_subscription_tier PRIMARY KEY (tier_id);


--
-- Name: sync_conflict_classification_matrix pk_sync_conflict_classification_matrix; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_conflict_classification_matrix
    ADD CONSTRAINT pk_sync_conflict_classification_matrix PRIMARY KEY (id);


--
-- Name: tech_availability pk_tech_availability; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tech_availability
    ADD CONSTRAINT pk_tech_availability PRIMARY KEY (id);


--
-- Name: tenant_calendar_integration pk_tenant_calendar_integration; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_calendar_integration
    ADD CONSTRAINT pk_tenant_calendar_integration PRIMARY KEY (id);


--
-- Name: tenant_email_branding pk_tenant_email_branding; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_email_branding
    ADD CONSTRAINT pk_tenant_email_branding PRIMARY KEY (tenant_id);


--
-- Name: tenant_legal_acceptance pk_tenant_legal_acceptance; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_legal_acceptance
    ADD CONSTRAINT pk_tenant_legal_acceptance PRIMARY KEY (acceptance_id);


--
-- Name: tenant_onboarding_checklist pk_tenant_onboarding_checklist; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_onboarding_checklist
    ADD CONSTRAINT pk_tenant_onboarding_checklist PRIMARY KEY (tenant_id);


--
-- Name: tenant_signup pk_tenant_signup; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_signup
    ADD CONSTRAINT pk_tenant_signup PRIMARY KEY (tenant_id);


--
-- Name: tenant_subscription_usage pk_tenant_subscription_usage; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_subscription_usage
    ADD CONSTRAINT pk_tenant_subscription_usage PRIMARY KEY (tenant_id, period_start);


--
-- Name: tenant_tier_override pk_tenant_tier_override; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_tier_override
    ADD CONSTRAINT pk_tenant_tier_override PRIMARY KEY (tenant_id);


--
-- Name: user_dashboard_widget pk_user_dashboard_widget; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_dashboard_widget
    ADD CONSTRAINT pk_user_dashboard_widget PRIMARY KEY (id);


--
-- Name: user_setting_override pk_user_setting_override; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_setting_override
    ADD CONSTRAINT pk_user_setting_override PRIMARY KEY (tenant_id, user_id, setting_key);


--
-- Name: voice_feedback pk_voice_feedback; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_feedback
    ADD CONSTRAINT pk_voice_feedback PRIMARY KEY (id);


--
-- Name: platform_role platform_role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_role
    ADD CONSTRAINT platform_role_pkey PRIMARY KEY (code);


--
-- Name: platform_setting_catalog platform_setting_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting_catalog
    ADD CONSTRAINT platform_setting_catalog_pkey PRIMARY KEY (key);


--
-- Name: platform_setting platform_setting_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting
    ADD CONSTRAINT platform_setting_pkey PRIMARY KEY (id);


--
-- Name: product_plan_product_feature_version pppfv_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_product_feature_version
    ADD CONSTRAINT pppfv_no_overlap EXCLUDE USING gist (product_plan_code WITH =, product_feature_code WITH =, valid_period WITH &&);


--
-- Name: pricebook_item pricebook_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT pricebook_item_pkey PRIMARY KEY (id);


--
-- Name: pricebook_item_version pricebook_item_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item_version
    ADD CONSTRAINT pricebook_item_version_pkey PRIMARY KEY (id);


--
-- Name: pricing_cache pricing_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache
    ADD CONSTRAINT pricing_cache_pkey PRIMARY KEY (id);


--
-- Name: product_feature product_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_feature
    ADD CONSTRAINT product_feature_pkey PRIMARY KEY (code);


--
-- Name: product_plan product_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan
    ADD CONSTRAINT product_plan_pkey PRIMARY KEY (code);


--
-- Name: product_plan_product_feature_version product_plan_product_feature_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_product_feature_version
    ADD CONSTRAINT product_plan_product_feature_version_pkey PRIMARY KEY (id);


--
-- Name: product_plan_version product_plan_version_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_version
    ADD CONSTRAINT product_plan_version_no_overlap EXCLUDE USING gist (product_plan_code WITH =, valid_period WITH &&);


--
-- Name: product_plan_version product_plan_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_version
    ADD CONSTRAINT product_plan_version_pkey PRIMARY KEY (id);


--
-- Name: psp_customer psp_customer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_customer
    ADD CONSTRAINT psp_customer_pkey PRIMARY KEY (id);


--
-- Name: psp_transaction_log psp_transaction_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_transaction_log
    ADD CONSTRAINT psp_transaction_log_pkey PRIMARY KEY (id);


--
-- Name: qco_line_type qco_line_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qco_line_type
    ADD CONSTRAINT qco_line_type_pkey PRIMARY KEY (id);


--
-- Name: qpl_contact_action_type qpl_contact_action_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qpl_contact_action_type
    ADD CONSTRAINT qpl_contact_action_type_pkey PRIMARY KEY (id);


--
-- Name: quote_acceptance quote_acceptance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT quote_acceptance_pkey PRIMARY KEY (id);


--
-- Name: quote_approval_comment quote_approval_comment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT quote_approval_comment_pkey PRIMARY KEY (id);


--
-- Name: quote_line quote_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_pkey PRIMARY KEY (id);


--
-- Name: quote_line_tax_component quote_line_tax_component_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line_tax_component
    ADD CONSTRAINT quote_line_tax_component_pkey PRIMARY KEY (id);


--
-- Name: quote_link_status quote_link_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_link_status
    ADD CONSTRAINT quote_link_status_pkey PRIMARY KEY (id);


--
-- Name: quote_message quote_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_message
    ADD CONSTRAINT quote_message_pkey PRIMARY KEY (id);


--
-- Name: quote_pending_edit quote_pending_edit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT quote_pending_edit_pkey PRIMARY KEY (id);


--
-- Name: quote quote_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT quote_pkey PRIMARY KEY (id);


--
-- Name: quote_public_link_contact_action quote_public_link_contact_action_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT quote_public_link_contact_action_pkey PRIMARY KEY (id);


--
-- Name: quote_public_link quote_public_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT quote_public_link_pkey PRIMARY KEY (id);


--
-- Name: quote_public_link quote_public_link_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT quote_public_link_token_hash_key UNIQUE (token_hash);


--
-- Name: quote_status quote_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_status
    ADD CONSTRAINT quote_status_pkey PRIMARY KEY (id);


--
-- Name: quote_template_line quote_template_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT quote_template_line_pkey PRIMARY KEY (id);


--
-- Name: quote_template quote_template_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template
    ADD CONSTRAINT quote_template_pkey PRIMARY KEY (id);


--
-- Name: quote_template_version quote_template_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_version
    ADD CONSTRAINT quote_template_version_pkey PRIMARY KEY (id);


--
-- Name: quote_version quote_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_version
    ADD CONSTRAINT quote_version_pkey PRIMARY KEY (id);


--
-- Name: site_lifecycle_status site_lifecycle_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_lifecycle_status
    ADD CONSTRAINT site_lifecycle_status_pkey PRIMARY KEY (id);


--
-- Name: site site_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site
    ADD CONSTRAINT site_pkey PRIMARY KEY (id);


--
-- Name: sms_quota_period sms_quota_period_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sms_quota_period
    ADD CONSTRAINT sms_quota_period_no_overlap EXCLUDE USING gist (tenant_id WITH =, tstzrange(period_start, period_end) WITH &&);


--
-- Name: sms_quota_period sms_quota_period_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sms_quota_period
    ADD CONSTRAINT sms_quota_period_pkey PRIMARY KEY (id);


--
-- Name: sso_provider sso_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_provider
    ADD CONSTRAINT sso_provider_pkey PRIMARY KEY (code);


--
-- Name: subscription subscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_pkey PRIMARY KEY (id);


--
-- Name: subscription subscription_psp_subscription_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_psp_subscription_id_key UNIQUE (psp_subscription_id);


--
-- Name: subscription_status subscription_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_status
    ADD CONSTRAINT subscription_status_pkey PRIMARY KEY (id);


--
-- Name: subscription_usage subscription_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT subscription_usage_pkey PRIMARY KEY (id);


--
-- Name: supplier_item_category supplier_item_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_category
    ADD CONSTRAINT supplier_item_category_pkey PRIMARY KEY (id);


--
-- Name: supplier_item supplier_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT supplier_item_pkey PRIMARY KEY (id);


--
-- Name: supplier_item_price supplier_item_price_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price
    ADD CONSTRAINT supplier_item_price_pkey PRIMARY KEY (id);


--
-- Name: supplier_item_uom supplier_item_uom_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_uom
    ADD CONSTRAINT supplier_item_uom_pkey PRIMARY KEY (id);


--
-- Name: supplier_lifecycle_status supplier_lifecycle_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_lifecycle_status
    ADD CONSTRAINT supplier_lifecycle_status_pkey PRIMARY KEY (id);


--
-- Name: supplier supplier_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier
    ADD CONSTRAINT supplier_pkey PRIMARY KEY (id);


--
-- Name: tax_rate_version tax_rate_version_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tax_rate_version
    ADD CONSTRAINT tax_rate_version_no_overlap EXCLUDE USING gist (jurisdiction_code WITH =, taxability_code WITH =, valid_period WITH &&);


--
-- Name: tax_rate_version tax_rate_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tax_rate_version
    ADD CONSTRAINT tax_rate_version_pkey PRIMARY KEY (id);


--
-- Name: taxability_code taxability_code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.taxability_code
    ADD CONSTRAINT taxability_code_pkey PRIMARY KEY (code);


--
-- Name: tenant_10dlc_profile tenant_10dlc_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_10dlc_profile
    ADD CONSTRAINT tenant_10dlc_profile_pkey PRIMARY KEY (tenant_id);


--
-- Name: tenant_domain tenant_domain_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_domain
    ADD CONSTRAINT tenant_domain_pkey PRIMARY KEY (id);


--
-- Name: tenant_markup_version tenant_markup_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_markup_version
    ADD CONSTRAINT tenant_markup_version_pkey PRIMARY KEY (id);


--
-- Name: tenant_messaging_registration tenant_messaging_registration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_messaging_registration
    ADD CONSTRAINT tenant_messaging_registration_pkey PRIMARY KEY (id);


--
-- Name: tenant_phone_number tenant_phone_number_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_phone_number
    ADD CONSTRAINT tenant_phone_number_pkey PRIMARY KEY (id);


--
-- Name: tenant tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT tenant_pkey PRIMARY KEY (id);


--
-- Name: tenant_product_feature_override tenant_product_feature_override_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_product_feature_override
    ADD CONSTRAINT tenant_product_feature_override_pkey PRIMARY KEY (tenant_id, product_feature_code);


--
-- Name: tenant_site tenant_site_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_site
    ADD CONSTRAINT tenant_site_pkey PRIMARY KEY (id);


--
-- Name: tenant_user_invite tenant_user_invite_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_invite
    ADD CONSTRAINT tenant_user_invite_pkey PRIMARY KEY (id);


--
-- Name: tenant_user tenant_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_pkey PRIMARY KEY (tenant_id, user_id);


--
-- Name: tenant_user_role tenant_user_role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_role
    ADD CONSTRAINT tenant_user_role_pkey PRIMARY KEY (code);


--
-- Name: tenant_user_status tenant_user_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_status
    ADD CONSTRAINT tenant_user_status_pkey PRIMARY KEY (id);


--
-- Name: tenant_markup_version tmv_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_markup_version
    ADD CONSTRAINT tmv_no_overlap EXCLUDE USING gist (tenant_id WITH =, job_expense_category_code WITH =, valid_period WITH &&);


--
-- Name: carrier_fee_schedule uq_carrier_fee_schedule_temporal; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_fee_schedule
    ADD CONSTRAINT uq_carrier_fee_schedule_temporal EXCLUDE USING gist (fee_code WITH =, entity_type WITH =, tstzrange(effective_from, effective_to) WITH &&);


--
-- Name: contact_portal_invite uq_contact_portal_invite_contact_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_portal_invite
    ADD CONSTRAINT uq_contact_portal_invite_contact_id UNIQUE (contact_id);


--
-- Name: customer_comm_template_type uq_customer_comm_template_type_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_comm_template_type
    ADD CONSTRAINT uq_customer_comm_template_type_slug UNIQUE (slug);


--
-- Name: customer_lifecycle_status uq_customer_lifecycle_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_lifecycle_status
    ADD CONSTRAINT uq_customer_lifecycle_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: customer uq_customer_tenant_display_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT uq_customer_tenant_display_name UNIQUE (tenant_id, display_name);


--
-- Name: entity_address uq_entity_address_entity_address; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT uq_entity_address_entity_address UNIQUE (entity_type_code, entity_id, address_id);


--
-- Name: entity_contact uq_entity_contact_entity_contact; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT uq_entity_contact_entity_contact UNIQUE (entity_type_code, entity_id, contact_id);


--
-- Name: integration_sync_mapping uq_integration_sync_mapping_external; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT uq_integration_sync_mapping_external UNIQUE (app_service_id, entity_type_code, external_id);


--
-- Name: integration_sync_mapping uq_integration_sync_mapping_internal; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT uq_integration_sync_mapping_internal UNIQUE (app_service_id, entity_type_code, entity_id);


--
-- Name: invoice_public_link uq_invoice_public_link_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT uq_invoice_public_link_token_hash UNIQUE (token_hash);


--
-- Name: invoice_status uq_invoice_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_status
    ADD CONSTRAINT uq_invoice_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: invoice uq_invoice_tenant_idempotency; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT uq_invoice_tenant_idempotency UNIQUE (tenant_id, idempotency_key);


--
-- Name: invoice uq_invoice_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT uq_invoice_tenant_number UNIQUE (tenant_id, invoice_number);


--
-- Name: job_status uq_job_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_status
    ADD CONSTRAINT uq_job_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: marketing_newsletter_subscriber uq_marketing_newsletter_subscriber_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketing_newsletter_subscriber
    ADD CONSTRAINT uq_marketing_newsletter_subscriber_email UNIQUE (email);


--
-- Name: marketing_waitlist_signup uq_marketing_waitlist_signup_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketing_waitlist_signup
    ADD CONSTRAINT uq_marketing_waitlist_signup_email UNIQUE (email);


--
-- Name: mobile_device_push_token uq_mobile_device_push_token_device_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT uq_mobile_device_push_token_device_id UNIQUE (device_id);


--
-- Name: payment_method uq_payment_method_tenant_psp; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT uq_payment_method_tenant_psp UNIQUE (tenant_id, psp_provider, psp_payment_method_id);


--
-- Name: payment_status uq_payment_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_status
    ADD CONSTRAINT uq_payment_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: payment uq_payment_stripe_payment_intent_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT uq_payment_stripe_payment_intent_id UNIQUE (stripe_payment_intent_id);


--
-- Name: payment uq_payment_tenant_idempotency; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT uq_payment_tenant_idempotency UNIQUE (tenant_id, idempotency_key);


--
-- Name: payment_type uq_payment_type_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_type
    ADD CONSTRAINT uq_payment_type_tenant_code UNIQUE (tenant_id, code);


--
-- Name: platform_setting uq_platform_setting_key_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting
    ADD CONSTRAINT uq_platform_setting_key_tenant UNIQUE (key, tenant_id);


--
-- Name: pricebook_item uq_pricebook_item_tenant_sku; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT uq_pricebook_item_tenant_sku UNIQUE (tenant_id, sku);


--
-- Name: pricing_cache uq_pricing_cache_supplier_sku_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache
    ADD CONSTRAINT uq_pricing_cache_supplier_sku_tenant UNIQUE NULLS NOT DISTINCT (supplier_id, sku, tenant_id);


--
-- Name: psp_customer uq_psp_customer_provider_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_customer
    ADD CONSTRAINT uq_psp_customer_provider_id UNIQUE (psp_provider, psp_customer_id);


--
-- Name: qpl_contact_action_type uq_qpl_contact_action_type_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qpl_contact_action_type
    ADD CONSTRAINT uq_qpl_contact_action_type_tenant_code UNIQUE (tenant_id, code);


--
-- Name: quote_acceptance uq_quote_acceptance_version_contact; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT uq_quote_acceptance_version_contact UNIQUE (quote_version_id, contact_id);


--
-- Name: quote_link_status uq_quote_link_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_link_status
    ADD CONSTRAINT uq_quote_link_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: quote_status uq_quote_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_status
    ADD CONSTRAINT uq_quote_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: quote_template uq_quote_template_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template
    ADD CONSTRAINT uq_quote_template_tenant_name UNIQUE (tenant_id, name);


--
-- Name: quote_template_version uq_quote_template_version_template_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_version
    ADD CONSTRAINT uq_quote_template_version_template_version UNIQUE (template_id, version_no);


--
-- Name: quote uq_quote_tenant_idempotency; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT uq_quote_tenant_idempotency UNIQUE (tenant_id, idempotency_key);


--
-- Name: quote_version uq_quote_version_quote_id_version_no; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_version
    ADD CONSTRAINT uq_quote_version_quote_id_version_no UNIQUE (quote_id, version_no);


--
-- Name: site_lifecycle_status uq_site_lifecycle_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_lifecycle_status
    ADD CONSTRAINT uq_site_lifecycle_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: stripe_webhook_event_processed uq_stripe_webhook_event_processed_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stripe_webhook_event_processed
    ADD CONSTRAINT uq_stripe_webhook_event_processed_id UNIQUE (id);


--
-- Name: subscription_status uq_subscription_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_status
    ADD CONSTRAINT uq_subscription_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: subscription_usage uq_subscription_usage_subscription_feature_period; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT uq_subscription_usage_subscription_feature_period UNIQUE (subscription_id, product_feature_code, period_start, period_end);


--
-- Name: supplier_item_category uq_supplier_item_category_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_category
    ADD CONSTRAINT uq_supplier_item_category_tenant_code UNIQUE (tenant_id, code);


--
-- Name: supplier_item uq_supplier_item_tenant_supplier_sku; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT uq_supplier_item_tenant_supplier_sku UNIQUE (tenant_id, supplier_id, sku);


--
-- Name: supplier_item_uom uq_supplier_item_uom_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_uom
    ADD CONSTRAINT uq_supplier_item_uom_tenant_code UNIQUE (tenant_id, code);


--
-- Name: supplier_lifecycle_status uq_supplier_lifecycle_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_lifecycle_status
    ADD CONSTRAINT uq_supplier_lifecycle_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: tenant_calendar_integration uq_tci_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_calendar_integration
    ADD CONSTRAINT uq_tci_tenant UNIQUE (tenant_id);


--
-- Name: tenant_domain uq_tenant_domain_tenant_id_domain; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_domain
    ADD CONSTRAINT uq_tenant_domain_tenant_id_domain UNIQUE (tenant_id, domain);


--
-- Name: tenant_messaging_registration uq_tenant_messaging_registration_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_messaging_registration
    ADD CONSTRAINT uq_tenant_messaging_registration_tenant UNIQUE (tenant_id);


--
-- Name: tenant_user_invite uq_tenant_user_invite_tenant_id_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_invite
    ADD CONSTRAINT uq_tenant_user_invite_tenant_id_email UNIQUE (tenant_id, email);


--
-- Name: tenant_user_status uq_tenant_user_status_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_status
    ADD CONSTRAINT uq_tenant_user_status_tenant_code UNIQUE (tenant_id, code);


--
-- Name: user uq_user_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT uq_user_email UNIQUE (email);


--
-- Name: user_mfa_method uq_user_mfa_method_tenant_user_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_method
    ADD CONSTRAINT uq_user_mfa_method_tenant_user_type UNIQUE (tenant_id, user_id, method_type);


--
-- Name: user_preference uq_user_preference_user_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_preference
    ADD CONSTRAINT uq_user_preference_user_tenant UNIQUE (user_id, tenant_id);


--
-- Name: user_sso_identity uq_user_sso_identity_provider_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sso_identity
    ADD CONSTRAINT uq_user_sso_identity_provider_user UNIQUE (sso_provider_code, provider_user_id);


--
-- Name: usage_ledger usage_ledger_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: usage_ledger usage_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_pkey PRIMARY KEY (id);


--
-- Name: user_endpoint user_endpoint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_endpoint
    ADD CONSTRAINT user_endpoint_pkey PRIMARY KEY (id);


--
-- Name: user_mfa_method user_mfa_method_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_method
    ADD CONSTRAINT user_mfa_method_pkey PRIMARY KEY (mfa_method_id);


--
-- Name: user_mfa_recovery_code user_mfa_recovery_code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_recovery_code
    ADD CONSTRAINT user_mfa_recovery_code_pkey PRIMARY KEY (code_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user_preference user_preference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_preference
    ADD CONSTRAINT user_preference_pkey PRIMARY KEY (id);


--
-- Name: user_session_history user_session_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session_history
    ADD CONSTRAINT user_session_history_pkey PRIMARY KEY (tenant_id, user_id);


--
-- Name: user_session_metadata user_session_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session_metadata
    ADD CONSTRAINT user_session_metadata_pkey PRIMARY KEY (session_id);


--
-- Name: user_sms_consent_audit user_sms_consent_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sms_consent_audit
    ADD CONSTRAINT user_sms_consent_audit_pkey PRIMARY KEY (id);


--
-- Name: user_sso_identity user_sso_identity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sso_identity
    ADD CONSTRAINT user_sso_identity_pkey PRIMARY KEY (id);


--
-- Name: voice_command_entity_link voice_command_entity_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_entity_link
    ADD CONSTRAINT voice_command_entity_link_pkey PRIMARY KEY (id);


--
-- Name: voice_command_log voice_command_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_log
    ADD CONSTRAINT voice_command_log_pkey PRIMARY KEY (id);


--
-- Name: webhook_delivery_attempt webhook_delivery_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_delivery_attempt
    ADD CONSTRAINT webhook_delivery_attempt_pkey PRIMARY KEY (id);


--
-- Name: webhook_endpoint webhook_endpoint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_endpoint
    ADD CONSTRAINT webhook_endpoint_pkey PRIMARY KEY (id);


--
-- Name: webhook_event webhook_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event
    ADD CONSTRAINT webhook_event_pkey PRIMARY KEY (id);


--
-- Name: webhook_event_type webhook_event_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event_type
    ADD CONSTRAINT webhook_event_type_pkey PRIMARY KEY (code);


--
-- Name: idx_audit_event_entity_search; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX idx_audit_event_entity_search ON audit.event USING btree (entity_name, entity_id, occurred_at DESC);


--
-- Name: idx_audit_event_tenant_time; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX idx_audit_event_tenant_time ON audit.event USING btree (tenant_id, occurred_at DESC);


--
-- Name: idx_audit_event_user_action_time; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX idx_audit_event_user_action_time ON audit.event USING btree (user_id, action, occurred_at DESC);


--
-- Name: ix_audit_event_idempotency_key; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX ix_audit_event_idempotency_key ON audit.event USING btree (idempotency_key);


--
-- Name: ix_audit_event_request_id; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX ix_audit_event_request_id ON audit.event USING btree (request_id);


--
-- Name: idx_calendar_sync_conflict_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_calendar_sync_conflict_pending ON public.calendar_sync_conflict USING btree (tenant_id, created_at) WHERE (resolution IS NULL);


--
-- Name: idx_calendar_sync_log_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_calendar_sync_log_entity ON public.calendar_sync_log USING btree (tenant_id, entity_type, entity_id, created_at DESC);


--
-- Name: idx_calendar_sync_log_tenant_recent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_calendar_sync_log_tenant_recent ON public.calendar_sync_log USING btree (tenant_id, created_at DESC);


--
-- Name: idx_change_order_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_change_order_created_at ON public.change_order USING btree (created_at DESC);


--
-- Name: idx_comm_message_direction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_message_direction ON public.customer_communication_message USING btree (thread_id, direction, received_at DESC);


--
-- Name: idx_comm_message_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_message_status ON public.customer_communication_message USING btree (thread_id, status);


--
-- Name: idx_comm_message_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_message_thread_id ON public.customer_communication_message USING btree (thread_id);


--
-- Name: idx_comm_thread_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_thread_customer_id ON public.customer_communication_thread USING btree (customer_id);


--
-- Name: idx_comm_thread_last_msg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_thread_last_msg ON public.customer_communication_thread USING btree (tenant_id, last_message_at DESC);


--
-- Name: idx_comm_thread_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_thread_tech_id ON public.customer_communication_thread USING btree (tech_id);


--
-- Name: idx_comm_thread_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_thread_tenant_id ON public.customer_communication_thread USING btree (tenant_id);


--
-- Name: idx_comm_unrouted_parked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_unrouted_parked_at ON public.customer_communication_unrouted USING btree (tenant_id, parked_at DESC);


--
-- Name: idx_comm_unrouted_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comm_unrouted_tenant_id ON public.customer_communication_unrouted USING btree (tenant_id, status);


--
-- Name: idx_communication_template_code_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_communication_template_code_channel ON public.communication_template USING btree (template_code, channel);


--
-- Name: idx_communication_template_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_communication_template_tenant_id ON public.communication_template USING btree (tenant_id);


--
-- Name: idx_connector_run_supplier_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_connector_run_supplier_started ON public.connector_run_log USING btree (supplier_id, started_at DESC);


--
-- Name: idx_connector_run_supplier_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_connector_run_supplier_status ON public.connector_run_log USING btree (supplier_id, status, started_at DESC);


--
-- Name: idx_conv_msg_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conv_msg_embedding ON public.conversation_message USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_conv_msg_session_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conv_msg_session_time ON public.conversation_message USING btree (session_id, created_at);


--
-- Name: idx_conv_session_context_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conv_session_context_embedding ON public.conversation_session USING hnsw (context_embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_conv_session_tenant_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conv_session_tenant_user ON public.conversation_session USING btree (tenant_id, user_id, updated_at DESC);


--
-- Name: idx_csc_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_csc_tenant ON public.calendar_sync_conflict USING btree (tenant_id);


--
-- Name: idx_csc_urgency_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_csc_urgency_pending ON public.calendar_sync_conflict USING btree (tenant_id, urgency_score DESC NULLS LAST) WHERE (resolution IS NULL);


--
-- Name: idx_customer_comm_template_type_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_comm_template_type_category ON public.customer_comm_template_type USING btree (category);


--
-- Name: idx_customer_comm_template_type_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_comm_template_type_is_active ON public.customer_comm_template_type USING btree (is_active);


--
-- Name: idx_customer_communication_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_communication_customer_id ON public.customer_communication USING btree (customer_id);


--
-- Name: idx_customer_communication_customer_sent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_communication_customer_sent ON public.customer_communication USING btree (customer_id, sent_at DESC NULLS LAST);


--
-- Name: idx_customer_communication_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_communication_job_id ON public.customer_communication USING btree (job_id) WHERE (job_id IS NOT NULL);


--
-- Name: idx_customer_communication_notification_outbox_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_communication_notification_outbox_id ON public.customer_communication USING btree (notification_outbox_id) WHERE (notification_outbox_id IS NOT NULL);


--
-- Name: idx_customer_communication_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_communication_tenant_id ON public.customer_communication USING btree (tenant_id);


--
-- Name: idx_customer_communication_tenant_sent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_communication_tenant_sent ON public.customer_communication USING btree (tenant_id, sent_at DESC NULLS LAST);


--
-- Name: idx_customer_last_assigned_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_last_assigned_tech_id ON public.customer USING btree (last_assigned_tech_id) WHERE (last_assigned_tech_id IS NOT NULL);


--
-- Name: idx_customer_sms_consent_audit_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_sms_consent_audit_customer ON public.customer_sms_consent_audit USING btree (customer_id);


--
-- Name: idx_customer_sms_consent_audit_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customer_sms_consent_audit_tenant ON public.customer_sms_consent_audit USING btree (tenant_id);


--
-- Name: idx_integration_cred_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_integration_cred_expires ON public.integration_credential USING btree (expires_at) WHERE (expires_at IS NOT NULL);


--
-- Name: idx_integration_sync_conflict_auto_expire; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_integration_sync_conflict_auto_expire ON public.integration_sync_conflict USING btree (tenant_id, auto_expire_at) WHERE (((status)::text = 'pending'::text) AND (auto_expire_at IS NOT NULL));


--
-- Name: idx_integration_sync_conflict_pre_warning; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_integration_sync_conflict_pre_warning ON public.integration_sync_conflict USING btree (tenant_id, pre_warning_at) WHERE (((status)::text = 'pending'::text) AND (pre_warning_at IS NOT NULL));


--
-- Name: idx_invoice_balance; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_balance ON public.invoice USING btree (balance_due_cents) WHERE (balance_due_cents > 0);


--
-- Name: idx_invoice_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_created_at ON public.invoice USING btree (created_at DESC);


--
-- Name: idx_invoice_line_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_line_source ON public.invoice_line USING btree (source_type, source_id);


--
-- Name: idx_invoice_public_link_contact; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_public_link_contact ON public.invoice_public_link USING btree (contact_id);


--
-- Name: idx_invoice_public_link_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_public_link_invoice ON public.invoice_public_link USING btree (invoice_id);


--
-- Name: idx_invoice_status_due_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_status_due_at ON public.invoice USING btree (status_id, due_at);


--
-- Name: idx_invoice_tenant_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_tenant_created_at ON public.invoice USING btree (tenant_id, created_at DESC);


--
-- Name: idx_invoice_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_tenant_status ON public.invoice USING btree (tenant_id, status_id);


--
-- Name: idx_isc_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_isc_tenant_status ON public.integration_sync_conflict USING btree (tenant_id, status);


--
-- Name: idx_isl_tenant_service; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_isl_tenant_service ON public.integration_sync_log USING btree (tenant_id, app_service_id, started_at DESC);


--
-- Name: idx_ism_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ism_entity ON public.integration_sync_mapping USING btree (entity_type_code, entity_id);


--
-- Name: idx_ism_external; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ism_external ON public.integration_sync_mapping USING btree (app_service_id, external_id);


--
-- Name: idx_job_expense_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_expense_tenant ON public.job_expense USING btree (tenant_id, incurred_at DESC);


--
-- Name: idx_job_expense_unbilled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_expense_unbilled ON public.job_expense USING btree (job_id) WHERE ((is_billable = true) AND (invoice_line_id IS NULL));


--
-- Name: idx_job_scheduled_range; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_scheduled_range ON public.job USING gist (tenant_id, tstzrange(scheduled_start_at, scheduled_end_at, '[)'::text)) WHERE (scheduled_start_at IS NOT NULL);


--
-- Name: idx_job_tech_assignment_user_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_tech_assignment_user_active ON public.job_tech_assignment USING btree (tenant_id, user_id) WHERE (is_active = true);


--
-- Name: idx_job_tenant_status_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_tenant_status_created_at ON public.job USING btree (tenant_id, status_id, created_at DESC);


--
-- Name: idx_jte_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jte_job ON public.job_time_entry USING btree (job_id);


--
-- Name: idx_jte_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jte_started_at ON public.job_time_entry USING btree (started_at DESC);


--
-- Name: idx_jte_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jte_user ON public.job_time_entry USING btree (user_id);


--
-- Name: idx_mobile_device_push_token_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_device_push_token_active ON public.mobile_device_push_token USING btree (tenant_id, user_id, device_id) WHERE (revoked_at IS NULL);


--
-- Name: idx_mobile_device_push_token_tenant_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_device_push_token_tenant_user ON public.mobile_device_push_token USING btree (tenant_id, user_id);


--
-- Name: idx_mobile_push_rate_limit_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_push_rate_limit_tenant ON public.mobile_push_rate_limit USING btree (tenant_id);


--
-- Name: idx_mobile_sync_event_audit_escalation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_sync_event_audit_escalation ON public.mobile_sync_event_audit USING btree (escalation_id);


--
-- Name: idx_mobile_sync_event_audit_tenant_resolver; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_sync_event_audit_tenant_resolver ON public.mobile_sync_event_audit USING btree (tenant_id, resolver_user_id, resolved_at DESC);


--
-- Name: idx_mobile_sync_session_device_recent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_sync_session_device_recent ON public.mobile_sync_session USING btree (device_id, started_at DESC);


--
-- Name: idx_mobile_sync_session_tenant_user_device; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mobile_sync_session_tenant_user_device ON public.mobile_sync_session USING btree (tenant_id, user_id, device_id, started_at DESC);


--
-- Name: idx_msg_read_state_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_msg_read_state_user ON public.customer_communication_message_read_state USING btree (user_id, message_id);


--
-- Name: idx_nec_calc_log_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nec_calc_log_job ON public.nec_calculation_log USING btree (job_id) WHERE (job_id IS NOT NULL);


--
-- Name: idx_nec_calc_log_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nec_calc_log_tenant_created ON public.nec_calculation_log USING btree (tenant_id, created_at DESC);


--
-- Name: idx_nec_calc_log_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nec_calc_log_user ON public.nec_calculation_log USING btree (user_id, created_at DESC);


--
-- Name: idx_notif_attempt_outbox_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_attempt_outbox_time ON public.notification_delivery_attempt USING btree (notification_outbox_id, attempted_at DESC);


--
-- Name: idx_notif_outbox_channel_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_outbox_channel_status ON public.notification_outbox USING btree (channel, status);


--
-- Name: idx_notif_outbox_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_outbox_created_at ON public.notification_outbox USING btree (created_at DESC);


--
-- Name: idx_notif_outbox_provider_msg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_outbox_provider_msg ON public.notification_outbox USING btree (provider_message_id);


--
-- Name: idx_notif_outbox_status_sched; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_outbox_status_sched ON public.notification_outbox USING btree (status, scheduled_at, next_attempt_at);


--
-- Name: idx_notif_outbox_tenant_type_hour; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_outbox_tenant_type_hour ON public.notification_outbox USING btree (tenant_id, created_at DESC) WHERE ((channel)::text = 'in_app'::text);


--
-- Name: idx_payment_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_created_at ON public.payment USING btree (created_at DESC);


--
-- Name: idx_pricing_cache_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_cache_tenant ON public.pricing_cache USING btree (tenant_id);


--
-- Name: idx_psp_tx_log_tenant_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_psp_tx_log_tenant_time ON public.psp_transaction_log USING btree (tenant_id, created_at DESC);


--
-- Name: idx_qpl_action_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qpl_action_created_at ON public.quote_public_link_contact_action USING btree (created_at DESC);


--
-- Name: idx_quote_message_tenant_quote_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quote_message_tenant_quote_time ON public.quote_message USING btree (tenant_id, quote_id, created_at DESC);


--
-- Name: idx_quote_tenant_status_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quote_tenant_status_created_at ON public.quote USING btree (tenant_id, status_id, created_at DESC);


--
-- Name: idx_quote_version_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quote_version_created_at ON public.quote_version USING btree (created_at DESC);


--
-- Name: idx_site_tenant_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_site_tenant_customer ON public.site USING btree (tenant_id, customer_id);


--
-- Name: idx_sms_quota_period_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sms_quota_period_tenant_active ON public.sms_quota_period USING btree (tenant_id, period_start DESC);


--
-- Name: idx_su_tenant_product_feature_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_su_tenant_product_feature_period ON public.subscription_usage USING btree (subscription_id, product_feature_code, period_end DESC);


--
-- Name: idx_tci_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tci_tenant ON public.tenant_calendar_integration USING btree (tenant_id);


--
-- Name: idx_tech_availability_time_range; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tech_availability_time_range ON public.tech_availability USING gist (tenant_id, user_id, tstzrange(starts_at, ends_at, '[)'::text)) WHERE ((availability_type = ANY (ARRAY['pto'::text, 'unavailable'::text])) AND (is_active = true));


--
-- Name: idx_tech_availability_user_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tech_availability_user_active ON public.tech_availability USING btree (tenant_id, user_id) WHERE (is_active = true);


--
-- Name: idx_tenant_markup_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tenant_markup_category ON public.tenant_markup_version USING btree (tenant_id, job_expense_category_code);


--
-- Name: idx_tenant_phone_number_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tenant_phone_number_phone ON public.tenant_phone_number USING btree (phone_number);


--
-- Name: idx_tenant_phone_number_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tenant_phone_number_tenant_id ON public.tenant_phone_number USING btree (tenant_id);


--
-- Name: idx_ul_subscription_product_feature_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ul_subscription_product_feature_time ON public.usage_ledger USING btree (subscription_id, product_feature_code, occurred_at DESC);


--
-- Name: idx_usage_ledger_tenant_feature; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_ledger_tenant_feature ON public.usage_ledger USING btree (tenant_id, product_feature_code, is_reported);


--
-- Name: idx_usage_ledger_unreported; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_ledger_unreported ON public.usage_ledger USING btree (tenant_id, product_feature_code, is_reported) WHERE (is_reported = false);


--
-- Name: idx_user_sso_provider_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_sso_provider_id ON public.user_sso_identity USING btree (sso_provider_code, provider_user_id);


--
-- Name: idx_voice_log_intent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_voice_log_intent ON public.voice_command_log USING btree (intent_detected);


--
-- Name: idx_voice_log_latency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_voice_log_latency ON public.voice_command_log USING btree (total_latency_ms);


--
-- Name: idx_voice_log_tenant_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_voice_log_tenant_time ON public.voice_command_log USING btree (tenant_id, created_at DESC);


--
-- Name: idx_webhook_delivery_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_delivery_pending ON public.webhook_delivery_attempt USING btree (status, next_attempt_after);


--
-- Name: idx_webhook_event_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_event_entity ON public.webhook_event USING btree (entity_type_code, entity_id, created_at DESC);


--
-- Name: idx_webhook_event_tenant_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_event_tenant_time ON public.webhook_event USING btree (tenant_id, created_at DESC);


--
-- Name: ix_address_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_address_tenant_id ON public.address USING btree (tenant_id);


--
-- Name: ix_address_type_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_address_type_tenant_id ON public.address_type USING btree (tenant_id);


--
-- Name: ix_app_service_category_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_service_category_code ON public.app_service USING btree (category_code);


--
-- Name: ix_app_service_external_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_service_external_account_id ON public.app_service USING btree (external_account_id);


--
-- Name: ix_app_service_provider_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_service_provider_code ON public.app_service USING btree (provider_code);


--
-- Name: ix_app_service_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_service_tenant_id ON public.app_service USING btree (tenant_id);


--
-- Name: ix_auth_api_token_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_api_token_tenant_id ON public.auth_api_token USING btree (tenant_id);


--
-- Name: ix_auth_api_token_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_api_token_user_id ON public.auth_api_token USING btree (user_id);


--
-- Name: ix_auth_email_verification_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_email_verification_contact_id ON public.auth_email_verification USING btree (contact_id);


--
-- Name: ix_auth_email_verification_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_email_verification_token_hash ON public.auth_email_verification USING btree (token_hash);


--
-- Name: ix_auth_email_verification_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_email_verification_user_id ON public.auth_email_verification USING btree (user_id);


--
-- Name: ix_auth_jwk_jwk_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_jwk_jwk_status_id ON public.auth_jwk USING btree (jwk_status_id);


--
-- Name: ix_auth_jwk_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_jwk_tenant_id ON public.auth_jwk USING btree (tenant_id);


--
-- Name: ix_auth_mfa_otp_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_mfa_otp_contact_id ON public.auth_mfa_otp USING btree (contact_id);


--
-- Name: ix_auth_mfa_otp_user_endpoint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_mfa_otp_user_endpoint_id ON public.auth_mfa_otp USING btree (user_endpoint_id);


--
-- Name: ix_auth_mfa_otp_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_mfa_otp_user_id ON public.auth_mfa_otp USING btree (user_id);


--
-- Name: ix_auth_password_history_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_password_history_contact_id ON public.auth_password_history USING btree (contact_id);


--
-- Name: ix_auth_password_history_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_password_history_user_id ON public.auth_password_history USING btree (user_id);


--
-- Name: ix_auth_password_reset_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_password_reset_contact_id ON public.auth_password_reset USING btree (contact_id);


--
-- Name: ix_auth_password_reset_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_password_reset_token_hash ON public.auth_password_reset USING btree (token_hash);


--
-- Name: ix_auth_password_reset_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_password_reset_user_id ON public.auth_password_reset USING btree (user_id);


--
-- Name: ix_auth_refresh_token_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_refresh_token_session_id ON public.auth_refresh_token USING btree (session_id);


--
-- Name: ix_auth_refresh_token_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_refresh_token_tenant_id ON public.auth_refresh_token USING btree (tenant_id);


--
-- Name: ix_auth_refresh_token_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_refresh_token_user_id ON public.auth_refresh_token USING btree (user_id);


--
-- Name: ix_change_order_attachment_change_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_attachment_change_order_id ON public.change_order_attachment USING btree (change_order_id);


--
-- Name: ix_change_order_attachment_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_attachment_tenant_id ON public.change_order_attachment USING btree (tenant_id);


--
-- Name: ix_change_order_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_job_id ON public.change_order USING btree (job_id);


--
-- Name: ix_change_order_line_change_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_change_order_id ON public.change_order_line USING btree (change_order_id);


--
-- Name: ix_change_order_line_pricebook_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_pricebook_item_id ON public.change_order_line USING btree (pricebook_item_id);


--
-- Name: ix_change_order_line_qco_line_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_qco_line_type_id ON public.change_order_line USING btree (qco_line_type_id);


--
-- Name: ix_change_order_line_supplier_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_supplier_id ON public.change_order_line USING btree (supplier_id);


--
-- Name: ix_change_order_line_supplier_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_supplier_item_id ON public.change_order_line USING btree (supplier_item_id);


--
-- Name: ix_change_order_line_tax_component_change_order_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_tax_component_change_order_line_id ON public.change_order_line_tax_component USING btree (change_order_line_id);


--
-- Name: ix_change_order_line_tax_component_tax_rate_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_tax_component_tax_rate_version_id ON public.change_order_line_tax_component USING btree (tax_rate_version_id);


--
-- Name: ix_change_order_line_tax_component_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_tax_component_tenant_id ON public.change_order_line_tax_component USING btree (tenant_id);


--
-- Name: ix_change_order_line_taxability_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_taxability_code ON public.change_order_line USING btree (taxability_code);


--
-- Name: ix_change_order_line_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_line_tenant_id ON public.change_order_line USING btree (tenant_id);


--
-- Name: ix_change_order_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_order_tenant_id ON public.change_order USING btree (tenant_id);


--
-- Name: ix_connector_config_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_connector_config_enabled ON public.connector_config USING btree (enabled);


--
-- Name: ix_contact_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_customer_id ON public.contact USING btree (customer_id);


--
-- Name: ix_contact_endpoint_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_endpoint_contact_id ON public.contact_endpoint USING btree (contact_id);


--
-- Name: ix_contact_endpoint_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_endpoint_tenant_id ON public.contact_endpoint USING btree (tenant_id);


--
-- Name: ix_contact_portal_invite_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_portal_invite_tenant_id ON public.contact_portal_invite USING btree (tenant_id);


--
-- Name: ix_contact_portal_invite_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_portal_invite_token_hash ON public.contact_portal_invite USING btree (token_hash);


--
-- Name: ix_contact_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_tenant_id ON public.contact USING btree (tenant_id);


--
-- Name: ix_contact_type_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_type_tenant_id ON public.contact_type USING btree (tenant_id);


--
-- Name: ix_conversation_message_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_message_tenant_id ON public.conversation_message USING btree (tenant_id);


--
-- Name: ix_conversation_session_archived_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_session_archived_at ON public.conversation_session USING btree (archived_at) WHERE (archived_at IS NOT NULL);


--
-- Name: ix_conversation_session_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_session_user_id ON public.conversation_session USING btree (user_id);


--
-- Name: ix_customer_lifecycle_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_lifecycle_status_id ON public.customer USING btree (lifecycle_status_id);


--
-- Name: ix_customer_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_tenant_id ON public.customer USING btree (tenant_id);


--
-- Name: ix_data_export_request_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_data_export_request_status ON public.data_export_request USING btree (status);


--
-- Name: ix_data_export_request_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_data_export_request_tenant_id ON public.data_export_request USING btree (tenant_id);


--
-- Name: ix_data_export_request_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_data_export_request_user_id ON public.data_export_request USING btree (user_id);


--
-- Name: ix_discount_version_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_discount_version_tenant_id ON public.discount_version USING btree (tenant_id);


--
-- Name: ix_email_template_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_template_category ON public.email_template USING btree (category);


--
-- Name: ix_entity_address_address_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_address_address_id ON public.entity_address USING btree (address_id);


--
-- Name: ix_entity_address_address_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_address_address_type_code ON public.entity_address USING btree (address_type_code);


--
-- Name: ix_entity_address_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_address_tenant_id ON public.entity_address USING btree (tenant_id);


--
-- Name: ix_entity_contact_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_contact_contact_id ON public.entity_contact USING btree (contact_id);


--
-- Name: ix_entity_contact_contact_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_contact_contact_type_code ON public.entity_contact USING btree (contact_type_code);


--
-- Name: ix_entity_contact_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entity_contact_tenant_id ON public.entity_contact USING btree (tenant_id);


--
-- Name: ix_feedback_submission_from_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_feedback_submission_from_session_id ON public.feedback_submission USING btree (from_help_chat_session_id) WHERE (from_help_chat_session_id IS NOT NULL);


--
-- Name: ix_feedback_submission_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_feedback_submission_tenant_id ON public.feedback_submission USING btree (tenant_id);


--
-- Name: ix_feedback_submission_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_feedback_submission_user_id ON public.feedback_submission USING btree (user_id);


--
-- Name: ix_help_article_audience; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_article_audience ON public.help_article USING gin (audience);


--
-- Name: ix_help_article_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_article_category ON public.help_article USING btree (category);


--
-- Name: ix_help_article_chunk_article_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_article_chunk_article_id ON public.help_article_chunk USING btree (article_id);


--
-- Name: ix_help_article_chunk_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_article_chunk_embedding_hnsw ON public.help_article_chunk USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: ix_help_chat_message_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_message_session_id ON public.help_chat_message USING btree (session_id);


--
-- Name: ix_help_chat_message_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_message_tenant_id ON public.help_chat_message USING btree (tenant_id);


--
-- Name: ix_help_chat_session_last_activity_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_session_last_activity_at ON public.help_chat_session USING btree (last_activity_at);


--
-- Name: ix_help_chat_session_pending_anonymization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_session_pending_anonymization ON public.help_chat_session USING btree (last_activity_at) WHERE (anonymized_at IS NULL);


--
-- Name: ix_help_chat_session_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_session_tenant_id ON public.help_chat_session USING btree (tenant_id);


--
-- Name: ix_help_chat_session_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_session_user_id ON public.help_chat_session USING btree (user_id);


--
-- Name: ix_help_chat_session_user_tenant_activity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_chat_session_user_tenant_activity ON public.help_chat_session USING btree (user_id, tenant_id, last_activity_at DESC) WHERE (anonymized_at IS NULL);


--
-- Name: ix_help_training_corpus_category_inferred; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_training_corpus_category_inferred ON public.help_training_corpus USING btree (category_inferred);


--
-- Name: ix_help_training_corpus_original_session_id_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_training_corpus_original_session_id_hash ON public.help_training_corpus USING btree (original_session_id_hash);


--
-- Name: ix_idempotency_key_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idempotency_key_tenant_id ON public.idempotency_key USING btree (tenant_id);


--
-- Name: ix_idempotency_key_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idempotency_key_user_id ON public.idempotency_key USING btree (user_id);


--
-- Name: ix_in_app_notif_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_in_app_notif_user_created ON public.in_app_notification USING btree (tenant_id, user_id, created_at DESC);


--
-- Name: ix_in_app_notif_user_unread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_in_app_notif_user_unread ON public.in_app_notification USING btree (tenant_id, user_id, created_at DESC) WHERE (read_at IS NULL);


--
-- Name: ix_integration_credential_app_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_credential_app_service_id ON public.integration_credential USING btree (app_service_id);


--
-- Name: ix_integration_credential_connection_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_credential_connection_status ON public.integration_credential USING btree (connection_status);


--
-- Name: ix_integration_credential_initiated_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_credential_initiated_by_user_id ON public.integration_credential USING btree (initiated_by_user_id);


--
-- Name: ix_integration_credential_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_credential_tenant_id ON public.integration_credential USING btree (tenant_id);


--
-- Name: ix_integration_sync_conflict_app_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_sync_conflict_app_service_id ON public.integration_sync_conflict USING btree (app_service_id);


--
-- Name: ix_integration_sync_conflict_entity_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_sync_conflict_entity_type_code ON public.integration_sync_conflict USING btree (entity_type_code);


--
-- Name: ix_integration_sync_conflict_resolved_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_sync_conflict_resolved_by ON public.integration_sync_conflict USING btree (resolved_by);


--
-- Name: ix_integration_sync_log_app_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_sync_log_app_service_id ON public.integration_sync_log USING btree (app_service_id);


--
-- Name: ix_integration_sync_mapping_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_integration_sync_mapping_tenant_id ON public.integration_sync_mapping USING btree (tenant_id);


--
-- Name: ix_invoice_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_currency ON public.invoice USING btree (currency);


--
-- Name: ix_invoice_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_customer_id ON public.invoice USING btree (customer_id);


--
-- Name: ix_invoice_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_job_id ON public.invoice USING btree (job_id);


--
-- Name: ix_invoice_line_invoice_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_invoice_id ON public.invoice_line USING btree (invoice_id);


--
-- Name: ix_invoice_line_pricebook_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_pricebook_item_id ON public.invoice_line USING btree (pricebook_item_id);


--
-- Name: ix_invoice_line_qco_line_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_qco_line_type_id ON public.invoice_line USING btree (qco_line_type_id);


--
-- Name: ix_invoice_line_tax_component_invoice_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_tax_component_invoice_line_id ON public.invoice_line_tax_component USING btree (invoice_line_id);


--
-- Name: ix_invoice_line_tax_component_tax_rate_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_tax_component_tax_rate_version_id ON public.invoice_line_tax_component USING btree (tax_rate_version_id);


--
-- Name: ix_invoice_line_tax_component_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_tax_component_tenant_id ON public.invoice_line_tax_component USING btree (tenant_id);


--
-- Name: ix_invoice_line_taxability_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_taxability_code ON public.invoice_line USING btree (taxability_code);


--
-- Name: ix_invoice_line_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_line_tenant_id ON public.invoice_line USING btree (tenant_id);


--
-- Name: ix_invoice_payment_schedule_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_payment_schedule_line_id ON public.invoice USING btree (payment_schedule_line_id);


--
-- Name: ix_invoice_public_link_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_public_link_tenant_id ON public.invoice_public_link USING btree (tenant_id);


--
-- Name: ix_invoice_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_quote_id ON public.invoice USING btree (quote_id);


--
-- Name: ix_invoice_signoff_tenant_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_signoff_tenant_invoice ON public.invoice_signoff USING btree (tenant_id, invoice_id);


--
-- Name: ix_invoice_site_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_site_id ON public.invoice USING btree (site_id);


--
-- Name: ix_job_attachment_file_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_attachment_file_hash ON public.job_attachment USING btree (created_by, job_id, file_hash) WHERE (file_hash IS NOT NULL);


--
-- Name: ix_job_attachment_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_attachment_job_id ON public.job_attachment USING btree (job_id);


--
-- Name: ix_job_attachment_natural_key_dedup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_attachment_natural_key_dedup ON public.job_attachment USING btree (created_by, job_id, created_at);


--
-- Name: ix_job_attachment_pending_uploads; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_attachment_pending_uploads ON public.job_attachment USING btree (tenant_id, job_id) WHERE (upload_status = ANY (ARRAY['pending_upload'::text, 'uploading'::text]));


--
-- Name: ix_job_attachment_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_attachment_tenant_id ON public.job_attachment USING btree (tenant_id);


--
-- Name: ix_job_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_customer_id ON public.job USING btree (customer_id);


--
-- Name: ix_job_expense_category_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_expense_category_tenant_id ON public.job_expense_category USING btree (tenant_id);


--
-- Name: ix_job_expense_invoice_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_expense_invoice_line_id ON public.job_expense USING btree (invoice_line_id);


--
-- Name: ix_job_expense_job_expense_category_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_expense_job_expense_category_code ON public.job_expense USING btree (job_expense_category_code);


--
-- Name: ix_job_expense_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_expense_job_id ON public.job_expense USING btree (job_id);


--
-- Name: ix_job_expense_natural_key_dedup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_expense_natural_key_dedup ON public.job_expense USING btree (user_id, job_id, incurred_at, cost_cents);


--
-- Name: ix_job_expense_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_expense_user_id ON public.job_expense USING btree (user_id);


--
-- Name: ix_job_job_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_job_type_id ON public.job USING btree (job_type_id);


--
-- Name: ix_job_notes_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_notes_job_id ON public.job_notes USING btree (job_id);


--
-- Name: ix_job_notes_natural_key_dedup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_notes_natural_key_dedup ON public.job_notes USING btree (created_by, job_id, created_at);


--
-- Name: ix_job_notes_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_notes_tenant_id ON public.job_notes USING btree (tenant_id);


--
-- Name: ix_job_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_quote_id ON public.job USING btree (quote_id);


--
-- Name: ix_job_quote_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_quote_version_id ON public.job USING btree (quote_version_id);


--
-- Name: ix_job_recurrence_rule_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_recurrence_rule_customer_id ON public.job_recurrence_rule USING btree (customer_id);


--
-- Name: ix_job_recurrence_rule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_recurrence_rule_id ON public.job USING btree (recurrence_rule_id);


--
-- Name: ix_job_recurrence_rule_next_job_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_recurrence_rule_next_job_at ON public.job_recurrence_rule USING btree (next_job_at) WHERE (is_active = true);


--
-- Name: ix_job_recurrence_rule_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_recurrence_rule_tenant_id ON public.job_recurrence_rule USING btree (tenant_id);


--
-- Name: ix_job_site_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_site_id ON public.job USING btree (site_id);


--
-- Name: ix_job_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_status_id ON public.job USING btree (status_id);


--
-- Name: ix_job_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_tenant_id ON public.job USING btree (tenant_id);


--
-- Name: ix_job_tenant_job_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_job_tenant_job_number ON public.job USING btree (tenant_id, job_number);


--
-- Name: ix_job_time_entry_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_time_entry_tenant_id ON public.job_time_entry USING btree (tenant_id);


--
-- Name: ix_job_type_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_type_tenant_id ON public.job_type USING btree (tenant_id);


--
-- Name: ix_jte_etc_not_null; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jte_etc_not_null ON public.job_time_entry USING btree (job_id, quote_line_id, created_at DESC) WHERE (hours_remaining_estimate IS NOT NULL);


--
-- Name: ix_jte_natural_key_dedup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jte_natural_key_dedup ON public.job_time_entry USING btree (user_id, job_id, started_at);


--
-- Name: ix_jte_quote_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jte_quote_line_id ON public.job_time_entry USING btree (quote_line_id);


--
-- Name: ix_labor_rate_version_tenant_skill; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_labor_rate_version_tenant_skill ON public.labor_rate_version USING btree (tenant_id, skill_level_code);


--
-- Name: ix_loto_confirmation_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_loto_confirmation_job_id ON public.loto_confirmation USING btree (job_id);


--
-- Name: ix_loto_confirmation_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_loto_confirmation_tenant_id ON public.loto_confirmation USING btree (tenant_id);


--
-- Name: ix_loto_confirmation_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_loto_confirmation_user_id ON public.loto_confirmation USING btree (user_id);


--
-- Name: ix_marketing_contact_submission_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_contact_submission_created_at ON public.marketing_contact_submission USING btree (created_at);


--
-- Name: ix_marketing_contact_submission_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_contact_submission_email ON public.marketing_contact_submission USING btree (email);


--
-- Name: ix_marketing_job_application_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_job_application_created_at ON public.marketing_job_application USING btree (created_at);


--
-- Name: ix_marketing_job_application_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_job_application_email ON public.marketing_job_application USING btree (email);


--
-- Name: ix_marketing_newsletter_subscriber_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_newsletter_subscriber_email ON public.marketing_newsletter_subscriber USING btree (email);


--
-- Name: ix_marketing_newsletter_subscriber_subscribed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_newsletter_subscriber_subscribed_at ON public.marketing_newsletter_subscriber USING btree (subscribed_at);


--
-- Name: ix_marketing_waitlist_signup_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_waitlist_signup_created_at ON public.marketing_waitlist_signup USING btree (created_at);


--
-- Name: ix_marketing_waitlist_signup_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marketing_waitlist_signup_email ON public.marketing_waitlist_signup USING btree (email);


--
-- Name: ix_mfa_grace_period_tracking_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mfa_grace_period_tracking_tenant_id ON public.mfa_grace_period_tracking USING btree (tenant_id);


--
-- Name: ix_mfa_grace_period_tracking_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mfa_grace_period_tracking_user_id ON public.mfa_grace_period_tracking USING btree (user_id);


--
-- Name: ix_mobile_push_perm_tenant_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mobile_push_perm_tenant_user ON public.mobile_push_permission_state USING btree (tenant_id, user_id);


--
-- Name: ix_mobile_sync_event_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mobile_sync_event_created_at ON public.mobile_sync_event USING btree (created_at);


--
-- Name: ix_mobile_sync_event_tenant_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mobile_sync_event_tenant_user_status ON public.mobile_sync_event USING btree (tenant_id, user_id, status);


--
-- Name: ix_mobile_sync_owner_escalation_conflict_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mobile_sync_owner_escalation_conflict_id ON public.mobile_sync_owner_escalation USING btree (conflict_id);


--
-- Name: ix_mobile_sync_owner_escalation_originating_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mobile_sync_owner_escalation_originating_user ON public.mobile_sync_owner_escalation USING btree (originating_user_id);


--
-- Name: ix_mobile_sync_owner_escalation_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mobile_sync_owner_escalation_tenant_status ON public.mobile_sync_owner_escalation USING btree (tenant_id, status);


--
-- Name: ix_notif_default_policy_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notif_default_policy_tenant_id ON public.notification_default_policy USING btree (tenant_id);


--
-- Name: ix_notif_outbox_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notif_outbox_category_id ON public.notification_outbox USING btree (category_id);


--
-- Name: ix_notif_outbox_sub_trigger_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notif_outbox_sub_trigger_id ON public.notification_outbox USING btree (sub_trigger_id) WHERE (sub_trigger_id IS NOT NULL);


--
-- Name: ix_notif_pref_category_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notif_pref_category_channel ON public.notification_preference USING btree (category_id, channel);


--
-- Name: ix_notif_pref_tenant_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notif_pref_tenant_user ON public.notification_preference USING btree (tenant_id, user_id);


--
-- Name: ix_notif_sub_trigger_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notif_sub_trigger_category_id ON public.notification_category_sub_trigger USING btree (category_id);


--
-- Name: ix_notification_delivery_attempt_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_delivery_attempt_tenant_id ON public.notification_delivery_attempt USING btree (tenant_id);


--
-- Name: ix_notification_event_entity_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_event_entity_type_code ON public.notification_event USING btree (entity_type_code);


--
-- Name: ix_notification_event_notification_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_event_notification_type_code ON public.notification_event USING btree (notification_type_code);


--
-- Name: ix_notification_event_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_event_tenant_id ON public.notification_event USING btree (tenant_id);


--
-- Name: ix_notification_outbox_contact_endpoint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_contact_endpoint_id ON public.notification_outbox USING btree (contact_endpoint_id);


--
-- Name: ix_notification_outbox_idempotency_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_idempotency_key ON public.notification_outbox USING btree (idempotency_key);


--
-- Name: ix_notification_outbox_notification_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_notification_event_id ON public.notification_outbox USING btree (notification_event_id);


--
-- Name: ix_notification_outbox_recipient_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_recipient_contact_id ON public.notification_outbox USING btree (recipient_contact_id);


--
-- Name: ix_notification_outbox_recipient_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_recipient_user_id ON public.notification_outbox USING btree (recipient_user_id);


--
-- Name: ix_notification_outbox_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_tenant_id ON public.notification_outbox USING btree (tenant_id);


--
-- Name: ix_notification_outbox_user_endpoint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_user_endpoint_id ON public.notification_outbox USING btree (user_endpoint_id);


--
-- Name: ix_notification_template_notification_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_template_notification_type_code ON public.notification_template USING btree (notification_type_code);


--
-- Name: ix_notification_template_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_template_tenant_id ON public.notification_template USING btree (tenant_id);


--
-- Name: ix_notification_type_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_type_tenant_id ON public.notification_type USING btree (tenant_id);


--
-- Name: ix_password_policy_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_policy_tenant_id ON public.password_policy USING btree (tenant_id);


--
-- Name: ix_payment_connector_config_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_connector_config_id ON public.payment USING btree (connector_config_id);


--
-- Name: ix_payment_invoice_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_invoice_id ON public.payment USING btree (invoice_id);


--
-- Name: ix_payment_method_billing_address_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_method_billing_address_id ON public.payment_method USING btree (billing_address_id);


--
-- Name: ix_payment_method_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_method_customer_id ON public.payment_method USING btree (customer_id);


--
-- Name: ix_payment_method_payment_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_method_payment_type_id ON public.payment_method USING btree (payment_type_id);


--
-- Name: ix_payment_payment_method_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_payment_method_id ON public.payment USING btree (payment_method_id);


--
-- Name: ix_payment_schedule_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_schedule_job_id ON public.payment_schedule USING btree (job_id);


--
-- Name: ix_payment_schedule_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_schedule_quote_id ON public.payment_schedule USING btree (quote_id);


--
-- Name: ix_payment_schedule_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_schedule_tenant_id ON public.payment_schedule USING btree (tenant_id);


--
-- Name: ix_payment_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_status_id ON public.payment USING btree (status_id);


--
-- Name: ix_payment_stripe_payment_intent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_stripe_payment_intent_id ON public.payment USING btree (stripe_payment_intent_id);


--
-- Name: ix_payment_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_tenant_id ON public.payment USING btree (tenant_id);


--
-- Name: ix_platform_setting_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_platform_setting_key ON public.platform_setting USING btree (key);


--
-- Name: ix_platform_setting_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_platform_setting_tenant ON public.platform_setting USING btree (tenant_id);


--
-- Name: ix_pricebook_item_taxability_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pricebook_item_taxability_code ON public.pricebook_item USING btree (taxability_code);


--
-- Name: ix_pricebook_item_uom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pricebook_item_uom_id ON public.pricebook_item USING btree (uom_id);


--
-- Name: ix_pricebook_item_version_pricebook_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pricebook_item_version_pricebook_item_id ON public.pricebook_item_version USING btree (pricebook_item_id);


--
-- Name: ix_pricing_cache_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pricing_cache_currency ON public.pricing_cache USING btree (currency);


--
-- Name: ix_product_plan_product_feature_version_product_feature_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_plan_product_feature_version_product_feature_code ON public.product_plan_product_feature_version USING btree (product_feature_code);


--
-- Name: ix_product_plan_version_product_plan_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_plan_version_product_plan_code ON public.product_plan_version USING btree (product_plan_code);


--
-- Name: ix_psl_schedule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psl_schedule_id ON public.payment_schedule_line USING btree (payment_schedule_id);


--
-- Name: ix_psl_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psl_tenant_id ON public.payment_schedule_line USING btree (tenant_id);


--
-- Name: ix_psp_customer_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psp_customer_customer_id ON public.psp_customer USING btree (customer_id);


--
-- Name: ix_psp_customer_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psp_customer_tenant_id ON public.psp_customer USING btree (tenant_id);


--
-- Name: ix_psp_transaction_log_app_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psp_transaction_log_app_service_id ON public.psp_transaction_log USING btree (app_service_id);


--
-- Name: ix_psp_transaction_log_payment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psp_transaction_log_payment_id ON public.psp_transaction_log USING btree (payment_id);


--
-- Name: ix_psp_transaction_log_psp_reference_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_psp_transaction_log_psp_reference_id ON public.psp_transaction_log USING btree (psp_reference_id);


--
-- Name: ix_public_link_short_code_link_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_public_link_short_code_link_id ON public.public_link_short_code USING btree (link_id);


--
-- Name: ix_qco_line_type_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_qco_line_type_tenant_id ON public.qco_line_type USING btree (tenant_id);


--
-- Name: ix_quote_acceptance_accepted_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_acceptance_accepted_by_user_id ON public.quote_acceptance USING btree (accepted_by_user_id);


--
-- Name: ix_quote_acceptance_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_acceptance_contact_id ON public.quote_acceptance USING btree (contact_id);


--
-- Name: ix_quote_acceptance_quote_public_link_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_acceptance_quote_public_link_id ON public.quote_acceptance USING btree (quote_public_link_id);


--
-- Name: ix_quote_acceptance_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_acceptance_tenant_id ON public.quote_acceptance USING btree (tenant_id);


--
-- Name: ix_quote_approval_comment_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_approval_comment_quote_id ON public.quote_approval_comment USING btree (quote_id);


--
-- Name: ix_quote_approval_comment_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_approval_comment_tenant ON public.quote_approval_comment USING btree (tenant_id);


--
-- Name: ix_quote_approval_comment_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_approval_comment_version ON public.quote_approval_comment USING btree (quote_version_id);


--
-- Name: ix_quote_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_currency ON public.quote USING btree (currency);


--
-- Name: ix_quote_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_customer_id ON public.quote USING btree (customer_id);


--
-- Name: ix_quote_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_expires_at ON public.quote USING btree (expires_at);


--
-- Name: ix_quote_line_parent_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_parent_line_id ON public.quote_line USING btree (parent_line_id);


--
-- Name: ix_quote_line_pricebook_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_pricebook_item_id ON public.quote_line USING btree (pricebook_item_id);


--
-- Name: ix_quote_line_qco_line_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_qco_line_type_id ON public.quote_line USING btree (qco_line_type_id);


--
-- Name: ix_quote_line_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_quote_id ON public.quote_line USING btree (quote_id);


--
-- Name: ix_quote_line_supplier_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_supplier_id ON public.quote_line USING btree (supplier_id);


--
-- Name: ix_quote_line_supplier_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_supplier_item_id ON public.quote_line USING btree (supplier_item_id);


--
-- Name: ix_quote_line_tax_component_quote_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_tax_component_quote_line_id ON public.quote_line_tax_component USING btree (quote_line_id);


--
-- Name: ix_quote_line_tax_component_tax_rate_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_tax_component_tax_rate_version_id ON public.quote_line_tax_component USING btree (tax_rate_version_id);


--
-- Name: ix_quote_line_tax_component_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_tax_component_tenant_id ON public.quote_line_tax_component USING btree (tenant_id);


--
-- Name: ix_quote_line_taxability_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_taxability_code ON public.quote_line USING btree (taxability_code);


--
-- Name: ix_quote_line_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_line_tenant_id ON public.quote_line USING btree (tenant_id);


--
-- Name: ix_quote_message_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_message_contact_id ON public.quote_message USING btree (contact_id);


--
-- Name: ix_quote_message_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_message_quote_id ON public.quote_message USING btree (quote_id);


--
-- Name: ix_quote_pending_edit_editor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_pending_edit_editor ON public.quote_pending_edit USING btree (editor_user_id, quote_version_id);


--
-- Name: ix_quote_pending_edit_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_pending_edit_quote_id ON public.quote_pending_edit USING btree (quote_id);


--
-- Name: ix_quote_pending_edit_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_pending_edit_tenant ON public.quote_pending_edit USING btree (tenant_id);


--
-- Name: ix_quote_public_link_contact_action_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_contact_action_contact_id ON public.quote_public_link_contact_action USING btree (contact_id);


--
-- Name: ix_quote_public_link_contact_action_qpl_contact_action_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_contact_action_qpl_contact_action_type_id ON public.quote_public_link_contact_action USING btree (qpl_contact_action_type_id);


--
-- Name: ix_quote_public_link_contact_action_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_contact_action_quote_id ON public.quote_public_link_contact_action USING btree (quote_id);


--
-- Name: ix_quote_public_link_contact_action_quote_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_contact_action_quote_version_id ON public.quote_public_link_contact_action USING btree (quote_version_id);


--
-- Name: ix_quote_public_link_contact_action_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_contact_action_tenant_id ON public.quote_public_link_contact_action USING btree (tenant_id);


--
-- Name: ix_quote_public_link_contact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_contact_id ON public.quote_public_link USING btree (contact_id);


--
-- Name: ix_quote_public_link_quote_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_quote_id ON public.quote_public_link USING btree (quote_id);


--
-- Name: ix_quote_public_link_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_status_id ON public.quote_public_link USING btree (status_id);


--
-- Name: ix_quote_public_link_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_public_link_tenant_id ON public.quote_public_link USING btree (tenant_id);


--
-- Name: ix_quote_site_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_site_id ON public.quote USING btree (site_id);


--
-- Name: ix_quote_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_status_id ON public.quote USING btree (status_id);


--
-- Name: ix_quote_template_line_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_template_line_parent ON public.quote_template_line USING btree (parent_line_id);


--
-- Name: ix_quote_template_line_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_template_line_template_id ON public.quote_template_line USING btree (quote_template_id);


--
-- Name: ix_quote_template_line_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_template_line_tenant_id ON public.quote_template_line USING btree (tenant_id);


--
-- Name: ix_quote_template_system_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_template_system_template_id ON public.quote_template USING btree (system_template_id);


--
-- Name: ix_quote_template_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_template_tenant_id ON public.quote_template USING btree (tenant_id);


--
-- Name: ix_quote_template_version_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_template_version_template_id ON public.quote_template_version USING btree (template_id);


--
-- Name: ix_quote_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_tenant_id ON public.quote USING btree (tenant_id);


--
-- Name: ix_quote_tenant_quote_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_quote_tenant_quote_number ON public.quote USING btree (tenant_id, quote_number);


--
-- Name: ix_quote_version_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quote_version_tenant_id ON public.quote_version USING btree (tenant_id);


--
-- Name: ix_site_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_site_customer_id ON public.site USING btree (customer_id);


--
-- Name: ix_site_lifecycle_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_site_lifecycle_status_id ON public.site USING btree (lifecycle_status_id);


--
-- Name: ix_subscription_product_plan_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_product_plan_code ON public.subscription USING btree (product_plan_code);


--
-- Name: ix_subscription_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_status_id ON public.subscription USING btree (status_id);


--
-- Name: ix_subscription_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_tenant_id ON public.subscription USING btree (tenant_id);


--
-- Name: ix_subscription_tier_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_tier_is_active ON public.subscription_tier USING btree (is_active);


--
-- Name: ix_subscription_tier_is_trial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_tier_is_trial ON public.subscription_tier USING btree (is_trial);


--
-- Name: ix_subscription_tier_product_plan_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_tier_product_plan_code ON public.subscription_tier USING btree (product_plan_code);


--
-- Name: ix_subscription_usage_product_feature_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_usage_product_feature_code ON public.subscription_usage USING btree (product_feature_code);


--
-- Name: ix_subscription_usage_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_usage_tenant_id ON public.subscription_usage USING btree (tenant_id);


--
-- Name: ix_supplier_item_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_category_id ON public.supplier_item USING btree (category_id);


--
-- Name: ix_supplier_item_price_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_price_currency ON public.supplier_item_price USING btree (currency);


--
-- Name: ix_supplier_item_price_supplier_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_price_supplier_item_id ON public.supplier_item_price USING btree (supplier_item_id);


--
-- Name: ix_supplier_item_price_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_price_tenant_id ON public.supplier_item_price USING btree (tenant_id);


--
-- Name: ix_supplier_item_sku; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_sku ON public.supplier_item USING btree (sku);


--
-- Name: ix_supplier_item_supplier_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_supplier_id ON public.supplier_item USING btree (supplier_id);


--
-- Name: ix_supplier_item_taxability_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_taxability_code ON public.supplier_item USING btree (taxability_code);


--
-- Name: ix_supplier_item_uom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_item_uom_id ON public.supplier_item USING btree (uom_id);


--
-- Name: ix_supplier_lifecycle_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_lifecycle_status_id ON public.supplier USING btree (lifecycle_status_id);


--
-- Name: ix_supplier_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_tenant_id ON public.supplier USING btree (tenant_id);


--
-- Name: ix_sync_conflict_matrix_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_conflict_matrix_active ON public.sync_conflict_classification_matrix USING btree (operation_type, trigger_condition) WHERE (is_active = true);


--
-- Name: ix_sync_conflict_matrix_tenant_op; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_conflict_matrix_tenant_op ON public.sync_conflict_classification_matrix USING btree (tenant_id, operation_type);


--
-- Name: ix_tax_rate_version_jurisdiction_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tax_rate_version_jurisdiction_code ON public.tax_rate_version USING btree (jurisdiction_code);


--
-- Name: ix_tenant_charter_member_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_tenant_charter_member_number ON public.tenant USING btree (charter_member_number) WHERE (charter_member_number IS NOT NULL);


--
-- Name: ix_tenant_current_subscription_tier_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_current_subscription_tier_id ON public.tenant USING btree (current_subscription_tier_id);


--
-- Name: ix_tenant_free_period_ends_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_free_period_ends_at ON public.tenant USING btree (free_period_ends_at) WHERE (free_period_ends_at IS NOT NULL);


--
-- Name: ix_tenant_legal_acceptance_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_legal_acceptance_tenant_id ON public.tenant_legal_acceptance USING btree (tenant_id);


--
-- Name: ix_tenant_legal_acceptance_user_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_legal_acceptance_user_document ON public.tenant_legal_acceptance USING btree (tenant_id, user_id, document_type);


--
-- Name: ix_tenant_product_feature_override_product_feature_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_product_feature_override_product_feature_code ON public.tenant_product_feature_override USING btree (product_feature_code);


--
-- Name: ix_tenant_signup_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_signup_state ON public.tenant_signup USING btree (signup_state);


--
-- Name: ix_tenant_subscription_usage_period_end; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_subscription_usage_period_end ON public.tenant_subscription_usage USING btree (tenant_id, period_end DESC);


--
-- Name: ix_tenant_user_invite_invited_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_user_invite_invited_by ON public.tenant_user_invite USING btree (invited_by);


--
-- Name: ix_tenant_user_invite_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_user_invite_token_hash ON public.tenant_user_invite USING btree (token_hash);


--
-- Name: ix_tenant_user_role_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_user_role_code ON public.tenant_user USING btree (role_code);


--
-- Name: ix_tenant_user_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_user_status_id ON public.tenant_user USING btree (status_id);


--
-- Name: ix_tenant_user_suspended_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_user_suspended_by ON public.tenant_user USING btree (suspended_by);


--
-- Name: ix_tenant_user_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_user_user_id ON public.tenant_user USING btree (user_id);


--
-- Name: ix_usage_ledger_product_feature_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_ledger_product_feature_code ON public.usage_ledger USING btree (product_feature_code);


--
-- Name: ix_user_dashboard_widget_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_dashboard_widget_tenant_id ON public.user_dashboard_widget USING btree (tenant_id);


--
-- Name: ix_user_dashboard_widget_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_dashboard_widget_user_id ON public.user_dashboard_widget USING btree (user_id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: ix_user_endpoint_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_endpoint_user_id ON public.user_endpoint USING btree (user_id);


--
-- Name: ix_user_mfa_method_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_mfa_method_tenant_id ON public.user_mfa_method USING btree (tenant_id);


--
-- Name: ix_user_mfa_method_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_mfa_method_user_id ON public.user_mfa_method USING btree (user_id);


--
-- Name: ix_user_mfa_recovery_code_set_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_mfa_recovery_code_set_id ON public.user_mfa_recovery_code USING btree (set_id);


--
-- Name: ix_user_mfa_recovery_code_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_mfa_recovery_code_tenant_id ON public.user_mfa_recovery_code USING btree (tenant_id);


--
-- Name: ix_user_mfa_recovery_code_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_mfa_recovery_code_user_id ON public.user_mfa_recovery_code USING btree (user_id);


--
-- Name: ix_user_platform_role_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_platform_role_code ON public."user" USING btree (platform_role_code);


--
-- Name: ix_user_preference_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_preference_tenant_id ON public.user_preference USING btree (tenant_id);


--
-- Name: ix_user_session_history_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_session_history_tenant_id ON public.user_session_history USING btree (tenant_id);


--
-- Name: ix_user_session_history_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_session_history_user_id ON public.user_session_history USING btree (user_id);


--
-- Name: ix_user_session_metadata_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_session_metadata_tenant_id ON public.user_session_metadata USING btree (tenant_id);


--
-- Name: ix_user_session_metadata_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_session_metadata_user_id ON public.user_session_metadata USING btree (user_id);


--
-- Name: ix_user_session_metadata_user_id_revoked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_session_metadata_user_id_revoked_at ON public.user_session_metadata USING btree (user_id, revoked_at);


--
-- Name: ix_user_setting_override_tenant_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_setting_override_tenant_key ON public.user_setting_override USING btree (tenant_id, setting_key);


--
-- Name: ix_user_setting_override_tenant_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_setting_override_tenant_user ON public.user_setting_override USING btree (tenant_id, user_id);


--
-- Name: ix_user_sms_consent_audit_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sms_consent_audit_tenant_id ON public.user_sms_consent_audit USING btree (tenant_id);


--
-- Name: ix_user_sms_consent_audit_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sms_consent_audit_user_id ON public.user_sms_consent_audit USING btree (user_id);


--
-- Name: ix_user_sso_identity_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sso_identity_user_id ON public.user_sso_identity USING btree (user_id);


--
-- Name: ix_vcel_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vcel_entity ON public.voice_command_entity_link USING btree (tenant_id, entity_type, entity_id);


--
-- Name: ix_vcel_voice_log; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vcel_voice_log ON public.voice_command_entity_link USING btree (voice_command_log_id);


--
-- Name: ix_voice_command_log_idempotency_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_voice_command_log_idempotency_uuid ON public.voice_command_log USING btree (idempotency_uuid) WHERE (idempotency_uuid IS NOT NULL);


--
-- Name: ix_voice_command_log_message_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voice_command_log_message_id ON public.voice_command_log USING btree (message_id);


--
-- Name: ix_voice_command_log_processing_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voice_command_log_processing_status ON public.voice_command_log USING btree (tenant_id, processing_status) WHERE (processing_status <> ALL (ARRAY['completed'::text, 'failed'::text]));


--
-- Name: ix_voice_command_log_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voice_command_log_user_id ON public.voice_command_log USING btree (user_id);


--
-- Name: ix_voice_feedback_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voice_feedback_tenant_id ON public.voice_feedback USING btree (tenant_id);


--
-- Name: ix_voice_feedback_unexported; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voice_feedback_unexported ON public.voice_feedback USING btree (exported_at) WHERE (exported_at IS NULL);


--
-- Name: ix_voice_feedback_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voice_feedback_user_id ON public.voice_feedback USING btree (user_id);


--
-- Name: ix_webhook_delivery_attempt_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_delivery_attempt_tenant_id ON public.webhook_delivery_attempt USING btree (tenant_id);


--
-- Name: ix_webhook_delivery_attempt_webhook_endpoint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_delivery_attempt_webhook_endpoint_id ON public.webhook_delivery_attempt USING btree (webhook_endpoint_id);


--
-- Name: ix_webhook_delivery_attempt_webhook_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_delivery_attempt_webhook_event_id ON public.webhook_delivery_attempt USING btree (webhook_event_id);


--
-- Name: ix_webhook_endpoint_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_endpoint_tenant_id ON public.webhook_endpoint USING btree (tenant_id);


--
-- Name: ix_webhook_event_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_event_event_id ON public.webhook_event USING btree (event_id);


--
-- Name: ix_webhook_event_event_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_event_event_type_code ON public.webhook_event USING btree (event_type_code);


--
-- Name: ix_webhook_event_source_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_event_source_app ON public.webhook_event USING btree (source_app);


--
-- Name: ix_webhook_event_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_event_tenant_id ON public.webhook_event USING btree (tenant_id);


--
-- Name: uq_comm_thread_routing_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_comm_thread_routing_key ON public.customer_communication_thread USING btree (tenant_id, customer_id, tech_id, tenant_phone_number_id) WHERE (status = 'active'::text);


--
-- Name: uq_communication_template_scope; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_communication_template_scope ON public.communication_template USING btree (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), template_code, channel) WHERE (is_active = true);


--
-- Name: uq_invoice_signoff_one_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_invoice_signoff_one_active ON public.invoice_signoff USING btree (invoice_id) WHERE (superseded_at IS NULL);


--
-- Name: uq_invoice_signoff_tenant_idempotency; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_invoice_signoff_tenant_idempotency ON public.invoice_signoff USING btree (tenant_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);


--
-- Name: uq_job_external_calendar_event; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_job_external_calendar_event ON public.job USING btree (tenant_id, external_calendar_event_id) WHERE (external_calendar_event_id IS NOT NULL);


--
-- Name: uq_job_tech_assignment_active_primary; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_job_tech_assignment_active_primary ON public.job_tech_assignment USING btree (tenant_id, job_id) WHERE ((is_active = true) AND (role = 'primary'::text));


--
-- Name: uq_job_tech_assignment_active_user; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_job_tech_assignment_active_user ON public.job_tech_assignment USING btree (tenant_id, job_id, user_id) WHERE (is_active = true);


--
-- Name: uq_job_type_platform_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_job_type_platform_code ON public.job_type USING btree (code) WHERE (tenant_id IS NULL);


--
-- Name: uq_job_type_tenant_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_job_type_tenant_code ON public.job_type USING btree (tenant_id, code) WHERE (tenant_id IS NOT NULL);


--
-- Name: uq_loto_confirmation_active_per_job_user; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_loto_confirmation_active_per_job_user ON public.loto_confirmation USING btree (job_id, user_id) WHERE (is_active = true);


--
-- Name: uq_loto_confirmation_natural_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_loto_confirmation_natural_key ON public.loto_confirmation USING btree (user_id, job_id, confirmed_at);


--
-- Name: uq_notif_default_policy_system; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notif_default_policy_system ON public.notification_default_policy USING btree (category_id, channel) WHERE (tenant_id IS NULL);


--
-- Name: uq_notif_default_policy_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notif_default_policy_tenant ON public.notification_default_policy USING btree (tenant_id, category_id, channel) WHERE (tenant_id IS NOT NULL);


--
-- Name: uq_notif_pref_tenant_level; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notif_pref_tenant_level ON public.notification_preference USING btree (tenant_id, category_id, channel) WHERE (user_id IS NULL);


--
-- Name: uq_notif_pref_user_level; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notif_pref_user_level ON public.notification_preference USING btree (tenant_id, user_id, category_id, channel) WHERE (user_id IS NOT NULL);


--
-- Name: uq_psl_invoice_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_psl_invoice_id ON public.payment_schedule_line USING btree (invoice_id) WHERE (invoice_id IS NOT NULL);


--
-- Name: uq_psl_schedule_sequence; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_psl_schedule_sequence ON public.payment_schedule_line USING btree (payment_schedule_id, sequence);


--
-- Name: uq_sync_conflict_matrix_platform_default; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_sync_conflict_matrix_platform_default ON public.sync_conflict_classification_matrix USING btree (operation_type, trigger_condition) WHERE (tenant_id IS NULL);


--
-- Name: uq_sync_conflict_matrix_tenant_override; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_sync_conflict_matrix_tenant_override ON public.sync_conflict_classification_matrix USING btree (operation_type, trigger_condition, tenant_id) WHERE (tenant_id IS NOT NULL);


--
-- Name: uq_tenant_phone_number_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_tenant_phone_number_active ON public.tenant_phone_number USING btree (tenant_id) WHERE (status = 'active'::text);


--
-- Name: uq_tenant_site_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_tenant_site_slug ON public.tenant_site USING btree (slug);


--
-- Name: uq_tenant_site_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_tenant_site_tenant ON public.tenant_site USING btree (tenant_id);


--
-- Name: uq_tenant_site_tenant_idempotency; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_tenant_site_tenant_idempotency ON public.tenant_site USING btree (tenant_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);


--
-- Name: ux_global_primary_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_global_primary_email ON public.user_endpoint USING btree (lower((value)::text)) WHERE (((channel)::text = 'email'::text) AND (is_primary = true));


--
-- Name: ux_user_email_primary; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_user_email_primary ON public.user_endpoint USING btree (user_id) WHERE (((channel)::text = 'email'::text) AND (is_primary = true));


--
-- Name: address audit_address_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_address_changes AFTER INSERT OR DELETE OR UPDATE ON public.address FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: app_service audit_app_service_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_app_service_changes AFTER INSERT OR DELETE OR UPDATE ON public.app_service FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_api_token audit_auth_api_token_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_api_token_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_api_token FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_email_verification audit_auth_email_verification_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_email_verification_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_email_verification FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_jwk audit_auth_jwk_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_jwk_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_jwk FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_mfa_otp audit_auth_mfa_otp_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_mfa_otp_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_mfa_otp FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_password_history audit_auth_password_history_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_password_history_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_password_history FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_password_reset audit_auth_password_reset_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_password_reset_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_password_reset FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: auth_refresh_token audit_auth_refresh_token_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_auth_refresh_token_changes AFTER INSERT OR DELETE OR UPDATE ON public.auth_refresh_token FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: calendar_sync_conflict audit_calendar_sync_conflict_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_calendar_sync_conflict_changes AFTER INSERT OR DELETE OR UPDATE ON public.calendar_sync_conflict FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: carrier_fee_schedule audit_carrier_fee_schedule_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_carrier_fee_schedule_changes AFTER INSERT OR DELETE OR UPDATE ON public.carrier_fee_schedule FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: change_order_attachment audit_change_order_attachment_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_change_order_attachment_changes AFTER INSERT OR DELETE OR UPDATE ON public.change_order_attachment FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: change_order audit_change_order_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_change_order_changes AFTER INSERT OR DELETE OR UPDATE ON public.change_order FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: change_order_line audit_change_order_line_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_change_order_line_changes AFTER INSERT OR DELETE OR UPDATE ON public.change_order_line FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: change_order_line_tax_component audit_change_order_line_tax_component_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_change_order_line_tax_component_changes AFTER INSERT OR DELETE OR UPDATE ON public.change_order_line_tax_component FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: communication_template audit_communication_template_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_communication_template_changes AFTER INSERT OR DELETE OR UPDATE ON public.communication_template FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: connector_config audit_connector_config_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_connector_config_changes AFTER INSERT OR DELETE OR UPDATE ON public.connector_config FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: connector_run_log audit_connector_run_log_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_connector_run_log_changes AFTER INSERT OR DELETE OR UPDATE ON public.connector_run_log FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: contact audit_contact_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_contact_changes AFTER INSERT OR DELETE OR UPDATE ON public.contact FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: contact_endpoint audit_contact_endpoint_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_contact_endpoint_changes AFTER INSERT OR DELETE OR UPDATE ON public.contact_endpoint FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: contact_portal_invite audit_contact_portal_invite_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_contact_portal_invite_changes AFTER INSERT OR DELETE OR UPDATE ON public.contact_portal_invite FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: conversation_message audit_conversation_message_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_conversation_message_changes AFTER INSERT OR DELETE OR UPDATE ON public.conversation_message FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: conversation_session audit_conversation_session_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_conversation_session_changes AFTER INSERT OR DELETE OR UPDATE ON public.conversation_session FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer audit_customer_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer_comm_template_type audit_customer_comm_template_type_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_comm_template_type_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer_comm_template_type FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer_communication audit_customer_communication_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_communication_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer_communication_message audit_customer_communication_message_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_communication_message_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_message FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer_communication_message_read_state audit_customer_communication_message_read_state_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_communication_message_read_state_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_message_read_state FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer_communication_thread audit_customer_communication_thread_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_communication_thread_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_thread FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: customer_communication_unrouted audit_customer_communication_unrouted_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_customer_communication_unrouted_changes AFTER INSERT OR DELETE OR UPDATE ON public.customer_communication_unrouted FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: data_export_request audit_data_export_request_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_data_export_request_changes AFTER INSERT OR DELETE OR UPDATE ON public.data_export_request FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: discount_version audit_discount_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_discount_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.discount_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: email_template audit_email_template_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_email_template_changes AFTER INSERT OR DELETE OR UPDATE ON public.email_template FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: entity_address audit_entity_address_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_entity_address_changes AFTER INSERT OR DELETE OR UPDATE ON public.entity_address FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: entity_contact audit_entity_contact_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_entity_contact_changes AFTER INSERT OR DELETE OR UPDATE ON public.entity_contact FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: feedback_submission audit_feedback_submission_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_feedback_submission_changes AFTER INSERT OR DELETE OR UPDATE ON public.feedback_submission FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: help_article audit_help_article_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_help_article_changes AFTER INSERT OR DELETE OR UPDATE ON public.help_article FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: help_article_chunk audit_help_article_chunk_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_help_article_chunk_changes AFTER INSERT OR DELETE OR UPDATE ON public.help_article_chunk FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: help_chat_message audit_help_chat_message_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_help_chat_message_changes AFTER INSERT OR DELETE OR UPDATE ON public.help_chat_message FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: help_chat_session audit_help_chat_session_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_help_chat_session_changes AFTER INSERT OR DELETE OR UPDATE ON public.help_chat_session FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: help_training_corpus audit_help_training_corpus_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_help_training_corpus_changes AFTER INSERT OR DELETE OR UPDATE ON public.help_training_corpus FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: in_app_notification audit_in_app_notification_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_in_app_notification_changes AFTER INSERT OR DELETE OR UPDATE ON public.in_app_notification FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: integration_credential audit_integration_credential_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_integration_credential_changes AFTER INSERT OR DELETE OR UPDATE ON public.integration_credential FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: integration_sync_conflict audit_integration_sync_conflict_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_integration_sync_conflict_changes AFTER INSERT OR DELETE OR UPDATE ON public.integration_sync_conflict FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: integration_sync_log audit_integration_sync_log_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_integration_sync_log_changes AFTER INSERT OR DELETE OR UPDATE ON public.integration_sync_log FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: integration_sync_mapping audit_integration_sync_mapping_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_integration_sync_mapping_changes AFTER INSERT OR DELETE OR UPDATE ON public.integration_sync_mapping FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: invoice audit_invoice_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_invoice_changes AFTER INSERT OR DELETE OR UPDATE ON public.invoice FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: invoice_line audit_invoice_line_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_invoice_line_changes AFTER INSERT OR DELETE OR UPDATE ON public.invoice_line FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: invoice_line_tax_component audit_invoice_line_tax_component_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_invoice_line_tax_component_changes AFTER INSERT OR DELETE OR UPDATE ON public.invoice_line_tax_component FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: invoice_public_link audit_invoice_public_link_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_invoice_public_link_changes AFTER INSERT OR DELETE OR UPDATE ON public.invoice_public_link FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_attachment audit_job_attachment_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_attachment_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_attachment FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job audit_job_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_changes AFTER INSERT OR DELETE OR UPDATE ON public.job FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_expense audit_job_expense_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_expense_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_expense FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_notes audit_job_notes_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_notes_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_notes FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_recurrence_rule audit_job_recurrence_rule_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_recurrence_rule_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_recurrence_rule FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_tech_assignment audit_job_tech_assignment_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_tech_assignment_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_tech_assignment FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_time_entry audit_job_time_entry_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_time_entry_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_time_entry FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: job_type audit_job_type_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_job_type_changes AFTER INSERT OR DELETE OR UPDATE ON public.job_type FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: labor_rate_version audit_labor_rate_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_labor_rate_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.labor_rate_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: loto_confirmation audit_loto_confirmation_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_loto_confirmation_changes AFTER INSERT OR DELETE OR UPDATE ON public.loto_confirmation FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: marketing_contact_submission audit_marketing_contact_submission_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_marketing_contact_submission_changes AFTER INSERT OR DELETE OR UPDATE ON public.marketing_contact_submission FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: marketing_newsletter_subscriber audit_marketing_newsletter_subscriber_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_marketing_newsletter_subscriber_changes AFTER INSERT OR DELETE OR UPDATE ON public.marketing_newsletter_subscriber FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: marketing_waitlist_signup audit_marketing_waitlist_signup_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_marketing_waitlist_signup_changes AFTER INSERT OR DELETE OR UPDATE ON public.marketing_waitlist_signup FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: mfa_grace_period_tracking audit_mfa_grace_period_tracking_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_mfa_grace_period_tracking_changes AFTER INSERT OR DELETE OR UPDATE ON public.mfa_grace_period_tracking FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: mobile_device_push_token audit_mobile_device_push_token_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_mobile_device_push_token_changes AFTER INSERT OR DELETE OR UPDATE ON public.mobile_device_push_token FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: mobile_push_permission_state audit_mobile_push_permission_state_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_mobile_push_permission_state_changes AFTER INSERT OR DELETE OR UPDATE ON public.mobile_push_permission_state FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: mobile_sync_event_audit audit_mobile_sync_event_audit_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_mobile_sync_event_audit_changes AFTER INSERT OR DELETE OR UPDATE ON public.mobile_sync_event_audit FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: mobile_sync_event audit_mobile_sync_event_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_mobile_sync_event_changes AFTER INSERT OR DELETE OR UPDATE ON public.mobile_sync_event FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: mobile_sync_owner_escalation audit_mobile_sync_owner_escalation_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_mobile_sync_owner_escalation_changes AFTER INSERT OR DELETE OR UPDATE ON public.mobile_sync_owner_escalation FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: nec_calculation_log audit_nec_calculation_log_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_nec_calculation_log_changes AFTER INSERT OR DELETE OR UPDATE ON public.nec_calculation_log FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_category audit_notification_category_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_category_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_category FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_category_sub_trigger audit_notification_category_sub_trigger_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_category_sub_trigger_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_category_sub_trigger FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_default_policy audit_notification_default_policy_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_default_policy_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_default_policy FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_delivery_attempt audit_notification_delivery_attempt_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_delivery_attempt_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_delivery_attempt FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_event audit_notification_event_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_event_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_event FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_outbox audit_notification_outbox_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_outbox_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_preference audit_notification_preference_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_preference_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_preference FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: notification_template audit_notification_template_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_notification_template_changes AFTER INSERT OR DELETE OR UPDATE ON public.notification_template FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: password_policy audit_password_policy_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_password_policy_changes AFTER INSERT OR DELETE OR UPDATE ON public.password_policy FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: payment audit_payment_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_payment_changes AFTER INSERT OR DELETE OR UPDATE ON public.payment FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: payment_method audit_payment_method_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_payment_method_changes AFTER INSERT OR DELETE OR UPDATE ON public.payment_method FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: payment_schedule audit_payment_schedule_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_payment_schedule_changes AFTER INSERT OR DELETE OR UPDATE ON public.payment_schedule FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: payment_schedule_line audit_payment_schedule_line_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_payment_schedule_line_changes AFTER INSERT OR DELETE OR UPDATE ON public.payment_schedule_line FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: platform_role audit_platform_role_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_platform_role_changes AFTER INSERT OR DELETE OR UPDATE ON public.platform_role FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();


--
-- Name: platform_setting_catalog audit_platform_setting_catalog_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_platform_setting_catalog_changes AFTER INSERT OR DELETE OR UPDATE ON public.platform_setting_catalog FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: platform_setting audit_platform_setting_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_platform_setting_changes AFTER INSERT OR DELETE OR UPDATE ON public.platform_setting FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: pricebook_item audit_pricebook_item_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_pricebook_item_changes AFTER INSERT OR DELETE OR UPDATE ON public.pricebook_item FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: pricebook_item_version audit_pricebook_item_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_pricebook_item_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.pricebook_item_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: pricing_cache audit_pricing_cache_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_pricing_cache_changes AFTER INSERT OR DELETE OR UPDATE ON public.pricing_cache FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: product_feature audit_product_feature_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_product_feature_changes AFTER INSERT OR DELETE OR UPDATE ON public.product_feature FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();


--
-- Name: product_plan audit_product_plan_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_product_plan_changes AFTER INSERT OR DELETE OR UPDATE ON public.product_plan FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();


--
-- Name: product_plan_product_feature_version audit_product_plan_product_feature_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_product_plan_product_feature_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.product_plan_product_feature_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: product_plan_version audit_product_plan_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_product_plan_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.product_plan_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: psp_customer audit_psp_customer_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_psp_customer_changes AFTER INSERT OR DELETE OR UPDATE ON public.psp_customer FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: psp_transaction_log audit_psp_transaction_log_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_psp_transaction_log_changes AFTER INSERT OR DELETE OR UPDATE ON public.psp_transaction_log FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_acceptance audit_quote_acceptance_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_acceptance_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_acceptance FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_approval_comment audit_quote_approval_comment_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_approval_comment_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_approval_comment FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote audit_quote_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_line audit_quote_line_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_line_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_line FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_line_tax_component audit_quote_line_tax_component_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_line_tax_component_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_line_tax_component FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_message audit_quote_message_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_message_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_message FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_pending_edit audit_quote_pending_edit_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_pending_edit_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_pending_edit FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_public_link audit_quote_public_link_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_public_link_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_public_link FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_public_link_contact_action audit_quote_public_link_contact_action_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_public_link_contact_action_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_public_link_contact_action FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_template audit_quote_template_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_template_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_template FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_template_line audit_quote_template_line_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_template_line_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_template_line FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_template_version audit_quote_template_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_template_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_template_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: quote_version audit_quote_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_quote_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.quote_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: site audit_site_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_site_changes AFTER INSERT OR DELETE OR UPDATE ON public.site FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: sms_quota_period audit_sms_quota_period_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_sms_quota_period_changes AFTER INSERT OR DELETE OR UPDATE ON public.sms_quota_period FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: sso_provider audit_sso_provider_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_sso_provider_changes AFTER INSERT OR DELETE OR UPDATE ON public.sso_provider FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();


--
-- Name: stripe_webhook_event_processed audit_stripe_webhook_event_processed_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_stripe_webhook_event_processed_changes AFTER INSERT OR DELETE OR UPDATE ON public.stripe_webhook_event_processed FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: subscription audit_subscription_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_subscription_changes AFTER INSERT OR DELETE OR UPDATE ON public.subscription FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: subscription_tier audit_subscription_tier_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_subscription_tier_changes AFTER INSERT OR DELETE OR UPDATE ON public.subscription_tier FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: subscription_usage audit_subscription_usage_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_subscription_usage_changes AFTER INSERT OR DELETE OR UPDATE ON public.subscription_usage FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: supplier audit_supplier_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_supplier_changes AFTER INSERT OR DELETE OR UPDATE ON public.supplier FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: supplier_item audit_supplier_item_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_supplier_item_changes AFTER INSERT OR DELETE OR UPDATE ON public.supplier_item FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: supplier_item_price audit_supplier_item_price_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_supplier_item_price_changes AFTER INSERT OR DELETE OR UPDATE ON public.supplier_item_price FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: sync_conflict_classification_matrix audit_sync_conflict_classification_matrix_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_sync_conflict_classification_matrix_changes AFTER INSERT OR DELETE OR UPDATE ON public.sync_conflict_classification_matrix FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tax_rate_version audit_tax_rate_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tax_rate_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.tax_rate_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tech_availability audit_tech_availability_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tech_availability_changes AFTER INSERT OR DELETE OR UPDATE ON public.tech_availability FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_calendar_integration audit_tenant_calendar_integration_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_calendar_integration_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_calendar_integration FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant audit_tenant_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_domain audit_tenant_domain_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_domain_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_domain FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_email_branding audit_tenant_email_branding_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_email_branding_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_email_branding FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_legal_acceptance audit_tenant_legal_acceptance_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_legal_acceptance_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_legal_acceptance FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_markup_version audit_tenant_markup_version_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_markup_version_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_markup_version FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_onboarding_checklist audit_tenant_onboarding_checklist_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_onboarding_checklist_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_onboarding_checklist FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_phone_number audit_tenant_phone_number_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_phone_number_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_phone_number FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_signup audit_tenant_signup_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_signup_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_signup FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_subscription_usage audit_tenant_subscription_usage_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_subscription_usage_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_subscription_usage FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_tier_override audit_tenant_tier_override_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_tier_override_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_tier_override FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_user_invite audit_tenant_user_invite_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_user_invite_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_user_invite FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: tenant_user_role audit_tenant_user_role_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_tenant_user_role_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_user_role FOR EACH ROW EXECUTE FUNCTION audit.log_changes_code_pk();


--
-- Name: usage_ledger audit_usage_ledger_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_usage_ledger_changes AFTER INSERT OR DELETE OR UPDATE ON public.usage_ledger FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user audit_user_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_changes AFTER INSERT OR DELETE OR UPDATE ON public."user" FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_dashboard_widget audit_user_dashboard_widget_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_dashboard_widget_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_dashboard_widget FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_endpoint audit_user_endpoint_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_endpoint_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_endpoint FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_mfa_method audit_user_mfa_method_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_mfa_method_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_mfa_method FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_mfa_recovery_code audit_user_mfa_recovery_code_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_mfa_recovery_code_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_mfa_recovery_code FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_preference audit_user_preference_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_preference_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_preference FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_session_history audit_user_session_history_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_session_history_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_session_history FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_session_metadata audit_user_session_metadata_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_session_metadata_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_session_metadata FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_setting_override audit_user_setting_override_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_setting_override_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_setting_override FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: user_sso_identity audit_user_sso_identity_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_user_sso_identity_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_sso_identity FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: voice_command_entity_link audit_voice_command_entity_link_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_voice_command_entity_link_changes AFTER INSERT OR DELETE OR UPDATE ON public.voice_command_entity_link FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: voice_command_log audit_voice_command_log_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_voice_command_log_changes AFTER INSERT OR DELETE OR UPDATE ON public.voice_command_log FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: voice_feedback audit_voice_feedback_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_voice_feedback_changes AFTER INSERT OR DELETE OR UPDATE ON public.voice_feedback FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: webhook_delivery_attempt audit_webhook_delivery_attempt_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_webhook_delivery_attempt_changes AFTER INSERT OR DELETE OR UPDATE ON public.webhook_delivery_attempt FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: webhook_endpoint audit_webhook_endpoint_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_webhook_endpoint_changes AFTER INSERT OR DELETE OR UPDATE ON public.webhook_endpoint FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: webhook_event audit_webhook_event_changes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_webhook_event_changes AFTER INSERT OR DELETE OR UPDATE ON public.webhook_event FOR EACH ROW EXECUTE FUNCTION audit.log_changes();


--
-- Name: email_template guard_email_template_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_email_template_created_immutable BEFORE UPDATE ON public.email_template FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: feedback_submission guard_feedback_submission_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_feedback_submission_created_immutable BEFORE UPDATE ON public.feedback_submission FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: help_chat_message guard_help_chat_message_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_help_chat_message_created_immutable BEFORE UPDATE ON public.help_chat_message FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: help_chat_session guard_help_chat_session_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_help_chat_session_created_immutable BEFORE UPDATE ON public.help_chat_session FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_recurrence_rule guard_job_recurrence_rule_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_job_recurrence_rule_created_immutable BEFORE UPDATE ON public.job_recurrence_rule FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_template_version guard_quote_template_version_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_quote_template_version_created_immutable BEFORE UPDATE ON public.quote_template_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_email_branding guard_tenant_email_branding_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guard_tenant_email_branding_created_immutable BEFORE UPDATE ON public.tenant_email_branding FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: change_order_line recalc_change_order_totals_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER recalc_change_order_totals_trigger AFTER INSERT OR DELETE OR UPDATE ON public.change_order_line FOR EACH ROW EXECUTE FUNCTION public.recalc_change_order_totals_fn();


--
-- Name: quote_line recalc_quote_totals_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER recalc_quote_totals_trigger AFTER INSERT OR DELETE OR UPDATE ON public.quote_line FOR EACH ROW EXECUTE FUNCTION public.recalc_quote_totals_fn();


--
-- Name: email_template set_email_template_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_email_template_updated_at BEFORE UPDATE ON public.email_template FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: help_chat_session set_help_chat_session_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_help_chat_session_updated_at BEFORE UPDATE ON public.help_chat_session FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_recurrence_rule set_job_recurrence_rule_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_job_recurrence_rule_updated_at BEFORE UPDATE ON public.job_recurrence_rule FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_email_branding set_tenant_email_branding_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_tenant_email_branding_updated_at BEFORE UPDATE ON public.tenant_email_branding FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_10dlc_profile set_updated_at_tenant_10dlc_profile; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_updated_at_tenant_10dlc_profile BEFORE UPDATE ON public.tenant_10dlc_profile FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_site set_updated_at_tenant_site; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_updated_at_tenant_site BEFORE UPDATE ON public.tenant_site FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_endpoint sync_user_email_from_endpoint_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sync_user_email_from_endpoint_trigger AFTER INSERT OR DELETE OR UPDATE ON public.user_endpoint FOR EACH ROW EXECUTE FUNCTION public.sync_user_email_from_endpoint_fn();


--
-- Name: address trg_address_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_address_guard_created_immutable BEFORE UPDATE ON public.address FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: address trg_address_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_address_set_updated_at BEFORE UPDATE ON public.address FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: address_type trg_address_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_address_type_guard_created_immutable BEFORE UPDATE ON public.address_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: address_type trg_address_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_address_type_set_updated_at BEFORE UPDATE ON public.address_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: app_service_category trg_app_service_category_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_service_category_guard_created_immutable BEFORE UPDATE ON public.app_service_category FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: app_service_category trg_app_service_category_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_service_category_set_updated_at BEFORE UPDATE ON public.app_service_category FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: app_service trg_app_service_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_service_guard_created_immutable BEFORE UPDATE ON public.app_service FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: app_service_provider trg_app_service_provider_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_service_provider_guard_created_immutable BEFORE UPDATE ON public.app_service_provider FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: app_service_provider trg_app_service_provider_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_service_provider_set_updated_at BEFORE UPDATE ON public.app_service_provider FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: app_service trg_app_service_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_service_set_updated_at BEFORE UPDATE ON public.app_service FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: auth_api_token trg_auth_api_token_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_api_token_guard_created_immutable BEFORE UPDATE ON public.auth_api_token FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: auth_email_verification trg_auth_email_verification_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_email_verification_guard_created_immutable BEFORE UPDATE ON public.auth_email_verification FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: auth_jwk trg_auth_jwk_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_jwk_guard_created_immutable BEFORE UPDATE ON public.auth_jwk FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: auth_mfa_otp trg_auth_mfa_otp_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_mfa_otp_guard_created_immutable BEFORE UPDATE ON public.auth_mfa_otp FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: auth_password_history trg_auth_password_history_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_password_history_guard_created_immutable BEFORE UPDATE ON public.auth_password_history FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: auth_password_reset trg_auth_password_reset_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_password_reset_guard_created_immutable BEFORE UPDATE ON public.auth_password_reset FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: auth_refresh_token trg_auth_refresh_token_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_refresh_token_guard_created_immutable BEFORE UPDATE ON public.auth_refresh_token FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: calendar_sync_conflict trg_calendar_sync_conflict_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_sync_conflict_guard_created_immutable BEFORE UPDATE ON public.calendar_sync_conflict FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: calendar_sync_conflict trg_calendar_sync_conflict_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_sync_conflict_set_updated_at BEFORE UPDATE ON public.calendar_sync_conflict FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: calendar_sync_log trg_calendar_sync_log_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_sync_log_guard_created_immutable BEFORE UPDATE ON public.calendar_sync_log FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: carrier_fee_schedule trg_carrier_fee_schedule_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_carrier_fee_schedule_guard_created_immutable BEFORE UPDATE ON public.carrier_fee_schedule FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: carrier_fee_schedule trg_carrier_fee_schedule_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_carrier_fee_schedule_set_updated_at BEFORE UPDATE ON public.carrier_fee_schedule FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: change_order_attachment trg_change_order_attachment_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_attachment_guard_created_immutable BEFORE UPDATE ON public.change_order_attachment FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: change_order_attachment trg_change_order_attachment_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_attachment_set_updated_at BEFORE UPDATE ON public.change_order_attachment FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: change_order trg_change_order_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_guard_created_immutable BEFORE UPDATE ON public.change_order FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: change_order_line trg_change_order_line_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_line_guard_created_immutable BEFORE UPDATE ON public.change_order_line FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: change_order_line trg_change_order_line_recalc_totals; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_line_recalc_totals AFTER INSERT OR DELETE OR UPDATE ON public.change_order_line FOR EACH ROW EXECUTE FUNCTION public.recalc_change_order_totals_fn();


--
-- Name: change_order_line trg_change_order_line_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_line_set_updated_at BEFORE UPDATE ON public.change_order_line FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: change_order_line_tax_component trg_change_order_line_tax_component_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_line_tax_component_guard_created_immutable BEFORE UPDATE ON public.change_order_line_tax_component FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: change_order_line_tax_component trg_change_order_line_tax_component_recalc_totals; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_line_tax_component_recalc_totals AFTER INSERT OR DELETE OR UPDATE ON public.change_order_line_tax_component FOR EACH ROW EXECUTE FUNCTION public.recalc_change_order_totals_fn();


--
-- Name: change_order trg_change_order_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_change_order_set_updated_at BEFORE UPDATE ON public.change_order FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: communication_template trg_communication_template_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_communication_template_guard_created_immutable BEFORE UPDATE ON public.communication_template FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: communication_template trg_communication_template_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_communication_template_set_updated_at BEFORE UPDATE ON public.communication_template FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: connector_config trg_connector_config_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_connector_config_guard_created_immutable BEFORE UPDATE ON public.connector_config FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: connector_config trg_connector_config_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_connector_config_set_updated_at BEFORE UPDATE ON public.connector_config FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: connector_run_log trg_connector_run_log_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_connector_run_log_guard_created_immutable BEFORE UPDATE ON public.connector_run_log FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: contact_endpoint trg_contact_endpoint_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_endpoint_guard_created_immutable BEFORE UPDATE ON public.contact_endpoint FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: contact_endpoint trg_contact_endpoint_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_endpoint_set_updated_at BEFORE UPDATE ON public.contact_endpoint FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: contact trg_contact_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_guard_created_immutable BEFORE UPDATE ON public.contact FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: contact_portal_invite trg_contact_portal_invite_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_portal_invite_guard_created_immutable BEFORE UPDATE ON public.contact_portal_invite FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: contact trg_contact_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_set_updated_at BEFORE UPDATE ON public.contact FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: contact_type trg_contact_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_type_guard_created_immutable BEFORE UPDATE ON public.contact_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: contact_type trg_contact_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_type_set_updated_at BEFORE UPDATE ON public.contact_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: conversation_message trg_conversation_message_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_conversation_message_guard_created_immutable BEFORE UPDATE ON public.conversation_message FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: conversation_session trg_conversation_session_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_conversation_session_guard_created_immutable BEFORE UPDATE ON public.conversation_session FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: conversation_session trg_conversation_session_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_conversation_session_set_updated_at BEFORE UPDATE ON public.conversation_session FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: currency trg_currency_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_currency_guard_created_immutable BEFORE UPDATE ON public.currency FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: currency trg_currency_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_currency_set_updated_at BEFORE UPDATE ON public.currency FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer_comm_template_type trg_customer_comm_template_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_comm_template_type_guard_created_immutable BEFORE UPDATE ON public.customer_comm_template_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_comm_template_type trg_customer_comm_template_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_comm_template_type_set_updated_at BEFORE UPDATE ON public.customer_comm_template_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer_communication trg_customer_communication_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_guard_created_immutable BEFORE UPDATE ON public.customer_communication FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_communication_message trg_customer_communication_message_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_message_guard_created_immutable BEFORE UPDATE ON public.customer_communication_message FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_communication_message_read_state trg_customer_communication_message_read_state_guard_created_imm; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_message_read_state_guard_created_imm BEFORE UPDATE ON public.customer_communication_message_read_state FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_communication_message trg_customer_communication_message_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_message_set_updated_at BEFORE UPDATE ON public.customer_communication_message FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer_communication trg_customer_communication_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_set_updated_at BEFORE UPDATE ON public.customer_communication FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer_communication_thread trg_customer_communication_thread_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_thread_guard_created_immutable BEFORE UPDATE ON public.customer_communication_thread FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_communication_thread trg_customer_communication_thread_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_thread_set_updated_at BEFORE UPDATE ON public.customer_communication_thread FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer_communication_unrouted trg_customer_communication_unrouted_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_unrouted_guard_created_immutable BEFORE UPDATE ON public.customer_communication_unrouted FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_communication_unrouted trg_customer_communication_unrouted_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_communication_unrouted_set_updated_at BEFORE UPDATE ON public.customer_communication_unrouted FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer trg_customer_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_guard_created_immutable BEFORE UPDATE ON public.customer FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_lifecycle_status trg_customer_lifecycle_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_lifecycle_status_guard_created_immutable BEFORE UPDATE ON public.customer_lifecycle_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: customer_lifecycle_status trg_customer_lifecycle_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_lifecycle_status_set_updated_at BEFORE UPDATE ON public.customer_lifecycle_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer trg_customer_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_customer_set_updated_at BEFORE UPDATE ON public.customer FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: data_export_request trg_data_export_request_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_data_export_request_guard_created_immutable BEFORE UPDATE ON public.data_export_request FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: data_export_request trg_data_export_request_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_data_export_request_set_updated_at BEFORE UPDATE ON public.data_export_request FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: discount_version trg_discount_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_discount_version_guard_created_immutable BEFORE UPDATE ON public.discount_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: entity_address trg_entity_address_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_entity_address_guard_created_immutable BEFORE UPDATE ON public.entity_address FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: entity_address trg_entity_address_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_entity_address_set_updated_at BEFORE UPDATE ON public.entity_address FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: entity_contact trg_entity_contact_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_entity_contact_guard_created_immutable BEFORE UPDATE ON public.entity_contact FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: entity_contact trg_entity_contact_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_entity_contact_set_updated_at BEFORE UPDATE ON public.entity_contact FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: entity_type trg_entity_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_entity_type_guard_created_immutable BEFORE UPDATE ON public.entity_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: entity_type trg_entity_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_entity_type_set_updated_at BEFORE UPDATE ON public.entity_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: idempotency_key trg_idempotency_key_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_idempotency_key_guard_created_immutable BEFORE UPDATE ON public.idempotency_key FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: in_app_notification trg_in_app_notification_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_in_app_notification_guard_created_immutable BEFORE UPDATE ON public.in_app_notification FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: integration_credential trg_integration_credential_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_credential_guard_created_immutable BEFORE UPDATE ON public.integration_credential FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: integration_credential trg_integration_credential_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_credential_set_updated_at BEFORE UPDATE ON public.integration_credential FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: integration_sync_conflict trg_integration_sync_conflict_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_sync_conflict_guard_created_immutable BEFORE UPDATE ON public.integration_sync_conflict FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: integration_sync_conflict trg_integration_sync_conflict_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_sync_conflict_set_updated_at BEFORE UPDATE ON public.integration_sync_conflict FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: integration_sync_log trg_integration_sync_log_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_sync_log_guard_created_immutable BEFORE UPDATE ON public.integration_sync_log FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: integration_sync_mapping trg_integration_sync_mapping_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_sync_mapping_guard_created_immutable BEFORE UPDATE ON public.integration_sync_mapping FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: integration_sync_mapping trg_integration_sync_mapping_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integration_sync_mapping_set_updated_at BEFORE UPDATE ON public.integration_sync_mapping FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: invoice trg_invoice_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_guard_created_immutable BEFORE UPDATE ON public.invoice FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: invoice_line trg_invoice_line_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_line_guard_created_immutable BEFORE UPDATE ON public.invoice_line FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: invoice_line trg_invoice_line_recalc_totals; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_line_recalc_totals AFTER INSERT OR DELETE OR UPDATE ON public.invoice_line FOR EACH ROW EXECUTE FUNCTION public.recalc_invoice_totals_fn();


--
-- Name: invoice_line_tax_component trg_invoice_line_tax_component_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_line_tax_component_guard_created_immutable BEFORE UPDATE ON public.invoice_line_tax_component FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: invoice_line_tax_component trg_invoice_line_tax_component_recalc_totals; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_line_tax_component_recalc_totals AFTER INSERT OR DELETE OR UPDATE ON public.invoice_line_tax_component FOR EACH ROW EXECUTE FUNCTION public.recalc_invoice_totals_fn();


--
-- Name: invoice_public_link trg_invoice_public_link_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_public_link_guard_created_immutable BEFORE UPDATE ON public.invoice_public_link FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: invoice_public_link trg_invoice_public_link_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_public_link_set_updated_at BEFORE UPDATE ON public.invoice_public_link FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: invoice trg_invoice_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_set_updated_at BEFORE UPDATE ON public.invoice FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: invoice_status trg_invoice_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_status_guard_created_immutable BEFORE UPDATE ON public.invoice_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: invoice_status trg_invoice_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_invoice_status_set_updated_at BEFORE UPDATE ON public.invoice_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_attachment trg_job_attachment_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_attachment_guard_created_immutable BEFORE UPDATE ON public.job_attachment FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_attachment trg_job_attachment_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_attachment_set_updated_at BEFORE UPDATE ON public.job_attachment FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_expense_category trg_job_expense_category_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_expense_category_guard_created_immutable BEFORE UPDATE ON public.job_expense_category FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_expense_category trg_job_expense_category_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_expense_category_set_updated_at BEFORE UPDATE ON public.job_expense_category FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_expense trg_job_expense_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_expense_guard_created_immutable BEFORE UPDATE ON public.job_expense FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_expense trg_job_expense_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_expense_set_updated_at BEFORE UPDATE ON public.job_expense FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job trg_job_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_guard_created_immutable BEFORE UPDATE ON public.job FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_notes trg_job_notes_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_notes_guard_created_immutable BEFORE UPDATE ON public.job_notes FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_notes trg_job_notes_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_notes_set_updated_at BEFORE UPDATE ON public.job_notes FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job trg_job_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_set_updated_at BEFORE UPDATE ON public.job FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_status trg_job_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_status_guard_created_immutable BEFORE UPDATE ON public.job_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_status trg_job_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_status_set_updated_at BEFORE UPDATE ON public.job_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_tech_assignment trg_job_tech_assignment_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_tech_assignment_guard_created_immutable BEFORE UPDATE ON public.job_tech_assignment FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_tech_assignment trg_job_tech_assignment_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_tech_assignment_set_updated_at BEFORE UPDATE ON public.job_tech_assignment FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_time_entry trg_job_time_entry_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_time_entry_guard_created_immutable BEFORE UPDATE ON public.job_time_entry FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_time_entry trg_job_time_entry_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_time_entry_set_updated_at BEFORE UPDATE ON public.job_time_entry FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: job_type trg_job_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_type_guard_created_immutable BEFORE UPDATE ON public.job_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: job_type trg_job_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_job_type_set_updated_at BEFORE UPDATE ON public.job_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: jwk_status trg_jwk_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_jwk_status_guard_created_immutable BEFORE UPDATE ON public.jwk_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: labor_rate_version trg_labor_rate_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_labor_rate_version_guard_created_immutable BEFORE UPDATE ON public.labor_rate_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: loto_confirmation trg_loto_confirmation_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_loto_confirmation_guard_created_immutable BEFORE UPDATE ON public.loto_confirmation FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: marketing_contact_submission trg_marketing_contact_submission_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_marketing_contact_submission_guard_created_immutable BEFORE UPDATE ON public.marketing_contact_submission FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: marketing_waitlist_signup trg_marketing_waitlist_signup_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_marketing_waitlist_signup_guard_created_immutable BEFORE UPDATE ON public.marketing_waitlist_signup FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mfa_grace_period_tracking trg_mfa_grace_period_tracking_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mfa_grace_period_tracking_guard_created_immutable BEFORE UPDATE ON public.mfa_grace_period_tracking FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mfa_grace_period_tracking trg_mfa_grace_period_tracking_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mfa_grace_period_tracking_set_updated_at BEFORE UPDATE ON public.mfa_grace_period_tracking FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: mobile_device_push_token trg_mobile_device_push_token_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_device_push_token_guard_created_immutable BEFORE UPDATE ON public.mobile_device_push_token FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mobile_device_push_token trg_mobile_device_push_token_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_device_push_token_set_updated_at BEFORE UPDATE ON public.mobile_device_push_token FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: mobile_push_permission_state trg_mobile_push_permission_state_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_push_permission_state_guard_created_immutable BEFORE UPDATE ON public.mobile_push_permission_state FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mobile_push_permission_state trg_mobile_push_permission_state_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_push_permission_state_set_updated_at BEFORE UPDATE ON public.mobile_push_permission_state FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: mobile_sync_event_audit trg_mobile_sync_event_audit_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_sync_event_audit_guard_created_immutable BEFORE UPDATE ON public.mobile_sync_event_audit FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mobile_sync_event trg_mobile_sync_event_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_sync_event_guard_created_immutable BEFORE UPDATE ON public.mobile_sync_event FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mobile_sync_owner_escalation trg_mobile_sync_owner_escalation_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_sync_owner_escalation_guard_created_immutable BEFORE UPDATE ON public.mobile_sync_owner_escalation FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: mobile_sync_owner_escalation trg_mobile_sync_owner_escalation_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_mobile_sync_owner_escalation_set_updated_at BEFORE UPDATE ON public.mobile_sync_owner_escalation FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: nec_calculation_log trg_nec_calc_log_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_nec_calc_log_guard_created_immutable BEFORE UPDATE ON public.nec_calculation_log FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: nec_calculation_log trg_nec_calc_log_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_nec_calc_log_updated_at BEFORE UPDATE ON public.nec_calculation_log FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_category trg_notification_category_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_category_guard_created_immutable BEFORE UPDATE ON public.notification_category FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_category trg_notification_category_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_category_set_updated_at BEFORE UPDATE ON public.notification_category FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_category_sub_trigger trg_notification_category_sub_trigger_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_category_sub_trigger_guard_created_immutable BEFORE UPDATE ON public.notification_category_sub_trigger FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_category_sub_trigger trg_notification_category_sub_trigger_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_category_sub_trigger_set_updated_at BEFORE UPDATE ON public.notification_category_sub_trigger FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_channel trg_notification_channel_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_channel_guard_created_immutable BEFORE UPDATE ON public.notification_channel FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_channel trg_notification_channel_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_channel_set_updated_at BEFORE UPDATE ON public.notification_channel FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_default_policy trg_notification_default_policy_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_default_policy_guard_created_immutable BEFORE UPDATE ON public.notification_default_policy FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_default_policy trg_notification_default_policy_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_default_policy_set_updated_at BEFORE UPDATE ON public.notification_default_policy FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_delivery_attempt trg_notification_delivery_attempt_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_delivery_attempt_guard_created_immutable BEFORE UPDATE ON public.notification_delivery_attempt FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_event trg_notification_event_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_event_guard_created_immutable BEFORE UPDATE ON public.notification_event FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_outbox trg_notification_outbox_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_outbox_guard_created_immutable BEFORE UPDATE ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_outbox trg_notification_outbox_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_outbox_set_updated_at BEFORE UPDATE ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_preference trg_notification_preference_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_preference_guard_created_immutable BEFORE UPDATE ON public.notification_preference FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_preference trg_notification_preference_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_preference_set_updated_at BEFORE UPDATE ON public.notification_preference FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_template trg_notification_template_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_template_guard_created_immutable BEFORE UPDATE ON public.notification_template FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_template trg_notification_template_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_template_set_updated_at BEFORE UPDATE ON public.notification_template FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: notification_type trg_notification_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_type_guard_created_immutable BEFORE UPDATE ON public.notification_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: notification_type trg_notification_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notification_type_set_updated_at BEFORE UPDATE ON public.notification_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: password_policy trg_password_policy_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_password_policy_guard_created_immutable BEFORE UPDATE ON public.password_policy FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: password_policy trg_password_policy_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_password_policy_set_updated_at BEFORE UPDATE ON public.password_policy FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment trg_payment_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_guard_created_immutable BEFORE UPDATE ON public.payment FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: payment_method trg_payment_method_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_method_guard_created_immutable BEFORE UPDATE ON public.payment_method FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: payment_method trg_payment_method_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_method_set_updated_at BEFORE UPDATE ON public.payment_method FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment_schedule trg_payment_schedule_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_schedule_guard_created_immutable BEFORE UPDATE ON public.payment_schedule FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: payment_schedule_line trg_payment_schedule_line_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_schedule_line_guard_created_immutable BEFORE UPDATE ON public.payment_schedule_line FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: payment_schedule_line trg_payment_schedule_line_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_schedule_line_set_updated_at BEFORE UPDATE ON public.payment_schedule_line FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment_schedule trg_payment_schedule_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_schedule_set_updated_at BEFORE UPDATE ON public.payment_schedule FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment trg_payment_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_set_updated_at BEFORE UPDATE ON public.payment FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment_status trg_payment_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_status_guard_created_immutable BEFORE UPDATE ON public.payment_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: payment_status trg_payment_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_status_set_updated_at BEFORE UPDATE ON public.payment_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment_type trg_payment_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_type_guard_created_immutable BEFORE UPDATE ON public.payment_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: payment_type trg_payment_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_type_set_updated_at BEFORE UPDATE ON public.payment_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: platform_role trg_platform_role_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_platform_role_guard_created_immutable BEFORE UPDATE ON public.platform_role FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: platform_role trg_platform_role_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_platform_role_set_updated_at BEFORE UPDATE ON public.platform_role FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: pricebook_item trg_pricebook_item_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pricebook_item_guard_created_immutable BEFORE UPDATE ON public.pricebook_item FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: pricebook_item trg_pricebook_item_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pricebook_item_set_updated_at BEFORE UPDATE ON public.pricebook_item FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: pricebook_item_version trg_pricebook_item_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pricebook_item_version_guard_created_immutable BEFORE UPDATE ON public.pricebook_item_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: pricing_cache trg_pricing_cache_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pricing_cache_guard_created_immutable BEFORE UPDATE ON public.pricing_cache FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: product_feature trg_product_feature_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_feature_guard_created_immutable BEFORE UPDATE ON public.product_feature FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: product_feature trg_product_feature_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_feature_set_updated_at BEFORE UPDATE ON public.product_feature FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: product_plan trg_product_plan_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_plan_guard_created_immutable BEFORE UPDATE ON public.product_plan FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: product_plan_product_feature_version trg_product_plan_product_feature_version_guard_created_immutabl; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_plan_product_feature_version_guard_created_immutabl BEFORE UPDATE ON public.product_plan_product_feature_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: product_plan trg_product_plan_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_plan_set_updated_at BEFORE UPDATE ON public.product_plan FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: product_plan_version trg_product_plan_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_plan_version_guard_created_immutable BEFORE UPDATE ON public.product_plan_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: psp_customer trg_psp_customer_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_psp_customer_guard_created_immutable BEFORE UPDATE ON public.psp_customer FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: psp_customer trg_psp_customer_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_psp_customer_set_updated_at BEFORE UPDATE ON public.psp_customer FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: psp_transaction_log trg_psp_transaction_log_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_psp_transaction_log_guard_created_immutable BEFORE UPDATE ON public.psp_transaction_log FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: qco_line_type trg_qco_line_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_qco_line_type_guard_created_immutable BEFORE UPDATE ON public.qco_line_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: qco_line_type trg_qco_line_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_qco_line_type_set_updated_at BEFORE UPDATE ON public.qco_line_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: qpl_contact_action_type trg_qpl_contact_action_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_qpl_contact_action_type_guard_created_immutable BEFORE UPDATE ON public.qpl_contact_action_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: qpl_contact_action_type trg_qpl_contact_action_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_qpl_contact_action_type_set_updated_at BEFORE UPDATE ON public.qpl_contact_action_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_acceptance trg_quote_acceptance_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_acceptance_guard_created_immutable BEFORE UPDATE ON public.quote_acceptance FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_approval_comment trg_quote_approval_comment_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_approval_comment_guard_created_immutable BEFORE UPDATE ON public.quote_approval_comment FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote trg_quote_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_guard_created_immutable BEFORE UPDATE ON public.quote FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_line trg_quote_line_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_line_guard_created_immutable BEFORE UPDATE ON public.quote_line FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_line trg_quote_line_recalc_totals; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_line_recalc_totals AFTER INSERT OR DELETE OR UPDATE ON public.quote_line FOR EACH ROW EXECUTE FUNCTION public.recalc_quote_totals_fn();


--
-- Name: quote_line trg_quote_line_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_line_set_updated_at BEFORE UPDATE ON public.quote_line FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_line_tax_component trg_quote_line_tax_component_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_line_tax_component_guard_created_immutable BEFORE UPDATE ON public.quote_line_tax_component FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_line_tax_component trg_quote_line_tax_component_recalc_totals; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_line_tax_component_recalc_totals AFTER INSERT OR DELETE OR UPDATE ON public.quote_line_tax_component FOR EACH ROW EXECUTE FUNCTION public.recalc_quote_totals_fn();


--
-- Name: quote_link_status trg_quote_link_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_link_status_guard_created_immutable BEFORE UPDATE ON public.quote_link_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_link_status trg_quote_link_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_link_status_set_updated_at BEFORE UPDATE ON public.quote_link_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_message trg_quote_message_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_message_guard_created_immutable BEFORE UPDATE ON public.quote_message FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_message trg_quote_message_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_message_set_updated_at BEFORE UPDATE ON public.quote_message FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_pending_edit trg_quote_pending_edit_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_pending_edit_guard_created_immutable BEFORE UPDATE ON public.quote_pending_edit FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_pending_edit trg_quote_pending_edit_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_pending_edit_set_updated_at BEFORE UPDATE ON public.quote_pending_edit FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_public_link_contact_action trg_quote_public_link_contact_action_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_public_link_contact_action_guard_created_immutable BEFORE UPDATE ON public.quote_public_link_contact_action FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_public_link trg_quote_public_link_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_public_link_guard_created_immutable BEFORE UPDATE ON public.quote_public_link FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_public_link trg_quote_public_link_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_public_link_set_updated_at BEFORE UPDATE ON public.quote_public_link FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote trg_quote_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_set_updated_at BEFORE UPDATE ON public.quote FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_status trg_quote_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_status_guard_created_immutable BEFORE UPDATE ON public.quote_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_status trg_quote_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_status_set_updated_at BEFORE UPDATE ON public.quote_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_template trg_quote_template_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_template_guard_created_immutable BEFORE UPDATE ON public.quote_template FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_template_line trg_quote_template_line_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_template_line_guard_created_immutable BEFORE UPDATE ON public.quote_template_line FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: quote_template_line trg_quote_template_line_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_template_line_set_updated_at BEFORE UPDATE ON public.quote_template_line FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_template trg_quote_template_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_template_set_updated_at BEFORE UPDATE ON public.quote_template FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: quote_version trg_quote_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quote_version_guard_created_immutable BEFORE UPDATE ON public.quote_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: site trg_site_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_site_guard_created_immutable BEFORE UPDATE ON public.site FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: site_lifecycle_status trg_site_lifecycle_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_site_lifecycle_status_guard_created_immutable BEFORE UPDATE ON public.site_lifecycle_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: site_lifecycle_status trg_site_lifecycle_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_site_lifecycle_status_set_updated_at BEFORE UPDATE ON public.site_lifecycle_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: site trg_site_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_site_set_updated_at BEFORE UPDATE ON public.site FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: sms_quota_period trg_sms_quota_period_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sms_quota_period_guard_created_immutable BEFORE UPDATE ON public.sms_quota_period FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: sms_quota_period trg_sms_quota_period_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sms_quota_period_set_updated_at BEFORE UPDATE ON public.sms_quota_period FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: change_order trg_soft_delete_change_order_to_change_order_line; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_change_order_to_change_order_line AFTER UPDATE OF is_active ON public.change_order FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_change_order_line();


--
-- Name: customer trg_soft_delete_customer_to_contact; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_customer_to_contact AFTER UPDATE OF is_active ON public.customer FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_contact();


--
-- Name: customer trg_soft_delete_customer_to_site; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_customer_to_site AFTER UPDATE OF is_active ON public.customer FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_site();


--
-- Name: invoice_line trg_soft_delete_invoice_line_to_tax_component; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_invoice_line_to_tax_component AFTER UPDATE OF is_active ON public.invoice_line FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_invoice_line_tax_component();


--
-- Name: invoice trg_soft_delete_invoice_to_invoice_line; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_invoice_to_invoice_line AFTER UPDATE OF is_active ON public.invoice FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_invoice_line();


--
-- Name: job trg_soft_delete_job_to_change_order; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_job_to_change_order AFTER UPDATE OF is_active ON public.job FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_change_order();


--
-- Name: job trg_soft_delete_job_to_job_expense; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_job_to_job_expense AFTER UPDATE OF is_active ON public.job FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_job_expense();


--
-- Name: quote_line trg_soft_delete_quote_line_to_tax_component; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_quote_line_to_tax_component AFTER UPDATE OF is_active ON public.quote_line FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_quote_line_tax_component();


--
-- Name: quote trg_soft_delete_quote_to_quote_line; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_soft_delete_quote_to_quote_line AFTER UPDATE OF is_active ON public.quote FOR EACH ROW WHEN (((old.is_active IS DISTINCT FROM new.is_active) AND (new.is_active = false))) EXECUTE FUNCTION public.cascade_soft_delete_to_quote_line();


--
-- Name: sso_provider trg_sso_provider_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sso_provider_guard_created_immutable BEFORE UPDATE ON public.sso_provider FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: sso_provider trg_sso_provider_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sso_provider_set_updated_at BEFORE UPDATE ON public.sso_provider FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: stripe_webhook_event_processed trg_stripe_webhook_event_processed_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_stripe_webhook_event_processed_guard_created_immutable BEFORE UPDATE ON public.stripe_webhook_event_processed FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: subscription trg_subscription_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_guard_created_immutable BEFORE UPDATE ON public.subscription FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: subscription trg_subscription_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_set_updated_at BEFORE UPDATE ON public.subscription FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: subscription_status trg_subscription_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_status_guard_created_immutable BEFORE UPDATE ON public.subscription_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: subscription_status trg_subscription_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_status_set_updated_at BEFORE UPDATE ON public.subscription_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: subscription_tier trg_subscription_tier_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_tier_guard_created_immutable BEFORE UPDATE ON public.subscription_tier FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: subscription_tier trg_subscription_tier_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_tier_set_updated_at BEFORE UPDATE ON public.subscription_tier FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: subscription_usage trg_subscription_usage_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_usage_guard_created_immutable BEFORE UPDATE ON public.subscription_usage FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: subscription_usage trg_subscription_usage_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subscription_usage_set_updated_at BEFORE UPDATE ON public.subscription_usage FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: supplier trg_supplier_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_guard_created_immutable BEFORE UPDATE ON public.supplier FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: supplier_item_category trg_supplier_item_category_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_category_guard_created_immutable BEFORE UPDATE ON public.supplier_item_category FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: supplier_item_category trg_supplier_item_category_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_category_set_updated_at BEFORE UPDATE ON public.supplier_item_category FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: supplier_item trg_supplier_item_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_guard_created_immutable BEFORE UPDATE ON public.supplier_item FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: supplier_item_price trg_supplier_item_price_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_price_guard_created_immutable BEFORE UPDATE ON public.supplier_item_price FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: supplier_item trg_supplier_item_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_set_updated_at BEFORE UPDATE ON public.supplier_item FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: supplier_item_uom trg_supplier_item_uom_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_uom_guard_created_immutable BEFORE UPDATE ON public.supplier_item_uom FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: supplier_item_uom trg_supplier_item_uom_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_item_uom_set_updated_at BEFORE UPDATE ON public.supplier_item_uom FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: supplier_lifecycle_status trg_supplier_lifecycle_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_lifecycle_status_guard_created_immutable BEFORE UPDATE ON public.supplier_lifecycle_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: supplier_lifecycle_status trg_supplier_lifecycle_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_lifecycle_status_set_updated_at BEFORE UPDATE ON public.supplier_lifecycle_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: supplier trg_supplier_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_supplier_set_updated_at BEFORE UPDATE ON public.supplier FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: sync_conflict_classification_matrix trg_sync_conflict_classification_matrix_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sync_conflict_classification_matrix_guard_created_immutable BEFORE UPDATE ON public.sync_conflict_classification_matrix FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: sync_conflict_classification_matrix trg_sync_conflict_classification_matrix_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sync_conflict_classification_matrix_set_updated_at BEFORE UPDATE ON public.sync_conflict_classification_matrix FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tax_rate_version trg_tax_rate_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tax_rate_version_guard_created_immutable BEFORE UPDATE ON public.tax_rate_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: taxability_code trg_taxability_code_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_taxability_code_guard_created_immutable BEFORE UPDATE ON public.taxability_code FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: taxability_code trg_taxability_code_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_taxability_code_set_updated_at BEFORE UPDATE ON public.taxability_code FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tech_availability trg_tech_availability_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tech_availability_guard_created_immutable BEFORE UPDATE ON public.tech_availability FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tech_availability trg_tech_availability_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tech_availability_set_updated_at BEFORE UPDATE ON public.tech_availability FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_calendar_integration trg_tenant_calendar_integration_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_calendar_integration_guard_created_immutable BEFORE UPDATE ON public.tenant_calendar_integration FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_calendar_integration trg_tenant_calendar_integration_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_calendar_integration_set_updated_at BEFORE UPDATE ON public.tenant_calendar_integration FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_domain trg_tenant_domain_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_domain_guard_created_immutable BEFORE UPDATE ON public.tenant_domain FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_domain trg_tenant_domain_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_domain_set_updated_at BEFORE UPDATE ON public.tenant_domain FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant trg_tenant_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_guard_created_immutable BEFORE UPDATE ON public.tenant FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_legal_acceptance trg_tenant_legal_acceptance_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_legal_acceptance_guard_created_immutable BEFORE UPDATE ON public.tenant_legal_acceptance FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_markup_version trg_tenant_markup_version_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_markup_version_guard_created_immutable BEFORE UPDATE ON public.tenant_markup_version FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_onboarding_checklist trg_tenant_onboarding_checklist_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_onboarding_checklist_guard_created_immutable BEFORE UPDATE ON public.tenant_onboarding_checklist FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_onboarding_checklist trg_tenant_onboarding_checklist_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_onboarding_checklist_set_updated_at BEFORE UPDATE ON public.tenant_onboarding_checklist FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_phone_number trg_tenant_phone_number_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_phone_number_guard_created_immutable BEFORE UPDATE ON public.tenant_phone_number FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_phone_number trg_tenant_phone_number_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_phone_number_set_updated_at BEFORE UPDATE ON public.tenant_phone_number FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_product_feature_override trg_tenant_product_feature_override_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_product_feature_override_guard_created_immutable BEFORE UPDATE ON public.tenant_product_feature_override FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_product_feature_override trg_tenant_product_feature_override_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_product_feature_override_set_updated_at BEFORE UPDATE ON public.tenant_product_feature_override FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant trg_tenant_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_set_updated_at BEFORE UPDATE ON public.tenant FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_signup trg_tenant_signup_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_signup_guard_created_immutable BEFORE UPDATE ON public.tenant_signup FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_signup trg_tenant_signup_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_signup_set_updated_at BEFORE UPDATE ON public.tenant_signup FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_subscription_usage trg_tenant_subscription_usage_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_subscription_usage_guard_created_immutable BEFORE UPDATE ON public.tenant_subscription_usage FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_subscription_usage trg_tenant_subscription_usage_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_subscription_usage_set_updated_at BEFORE UPDATE ON public.tenant_subscription_usage FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_tier_override trg_tenant_tier_override_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_tier_override_guard_created_immutable BEFORE UPDATE ON public.tenant_tier_override FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_tier_override trg_tenant_tier_override_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_tier_override_set_updated_at BEFORE UPDATE ON public.tenant_tier_override FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_user trg_tenant_user_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_guard_created_immutable BEFORE UPDATE ON public.tenant_user FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_user trg_tenant_user_guard_platform_biu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_guard_platform_biu BEFORE INSERT OR UPDATE ON public.tenant_user FOR EACH ROW EXECUTE FUNCTION public.guard_tenant_user_platform_isolation();


--
-- Name: tenant_user_invite trg_tenant_user_invite_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_invite_guard_created_immutable BEFORE UPDATE ON public.tenant_user_invite FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_user_invite trg_tenant_user_invite_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_invite_set_updated_at BEFORE UPDATE ON public.tenant_user_invite FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_user_role trg_tenant_user_role_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_role_guard_created_immutable BEFORE UPDATE ON public.tenant_user_role FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_user_role trg_tenant_user_role_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_role_set_updated_at BEFORE UPDATE ON public.tenant_user_role FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_user trg_tenant_user_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_set_updated_at BEFORE UPDATE ON public.tenant_user FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tenant_user_status trg_tenant_user_status_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_status_guard_created_immutable BEFORE UPDATE ON public.tenant_user_status FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: tenant_user_status trg_tenant_user_status_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tenant_user_status_set_updated_at BEFORE UPDATE ON public.tenant_user_status FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: usage_ledger trg_usage_ledger_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_usage_ledger_guard_created_immutable BEFORE UPDATE ON public.usage_ledger FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_dashboard_widget trg_user_dashboard_widget_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_dashboard_widget_set_updated_at BEFORE UPDATE ON public.user_dashboard_widget FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_endpoint trg_user_endpoint_guard_bd; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_endpoint_guard_bd BEFORE DELETE ON public.user_endpoint FOR EACH ROW EXECUTE FUNCTION public.guard_user_endpoint_primary_email_fn();


--
-- Name: user_endpoint trg_user_endpoint_guard_biu; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_endpoint_guard_biu BEFORE INSERT OR UPDATE ON public.user_endpoint FOR EACH ROW EXECUTE FUNCTION public.guard_user_endpoint_primary_email_fn();


--
-- Name: user_endpoint trg_user_endpoint_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_endpoint_guard_created_immutable BEFORE UPDATE ON public.user_endpoint FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_endpoint trg_user_endpoint_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_endpoint_set_updated_at BEFORE UPDATE ON public.user_endpoint FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user trg_user_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_guard_created_immutable BEFORE UPDATE ON public."user" FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_mfa_method trg_user_mfa_method_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_mfa_method_guard_created_immutable BEFORE UPDATE ON public.user_mfa_method FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_mfa_method trg_user_mfa_method_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_mfa_method_set_updated_at BEFORE UPDATE ON public.user_mfa_method FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_mfa_recovery_code trg_user_mfa_recovery_code_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_mfa_recovery_code_guard_created_immutable BEFORE UPDATE ON public.user_mfa_recovery_code FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_preference trg_user_preference_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_preference_guard_created_immutable BEFORE UPDATE ON public.user_preference FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_preference trg_user_preference_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_preference_set_updated_at BEFORE UPDATE ON public.user_preference FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_session_history trg_user_session_history_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_session_history_guard_created_immutable BEFORE UPDATE ON public.user_session_history FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_session_history trg_user_session_history_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_session_history_set_updated_at BEFORE UPDATE ON public.user_session_history FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_session_metadata trg_user_session_metadata_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_session_metadata_guard_created_immutable BEFORE UPDATE ON public.user_session_metadata FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_session_metadata trg_user_session_metadata_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_session_metadata_set_updated_at BEFORE UPDATE ON public.user_session_metadata FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user trg_user_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_set_updated_at BEFORE UPDATE ON public."user" FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_setting_override trg_user_setting_override_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_setting_override_guard_created_immutable BEFORE UPDATE ON public.user_setting_override FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_setting_override trg_user_setting_override_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_setting_override_set_updated_at BEFORE UPDATE ON public.user_setting_override FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: user_sso_identity trg_user_sso_identity_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_sso_identity_guard_created_immutable BEFORE UPDATE ON public.user_sso_identity FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: user_sso_identity trg_user_sso_identity_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_sso_identity_set_updated_at BEFORE UPDATE ON public.user_sso_identity FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: voice_command_entity_link trg_voice_command_entity_link_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_voice_command_entity_link_guard_created_immutable BEFORE UPDATE ON public.voice_command_entity_link FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: voice_command_log trg_voice_command_log_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_voice_command_log_guard_created_immutable BEFORE UPDATE ON public.voice_command_log FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: voice_feedback trg_voice_feedback_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_voice_feedback_guard_created_immutable BEFORE UPDATE ON public.voice_feedback FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: webhook_delivery_attempt trg_webhook_delivery_attempt_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_webhook_delivery_attempt_guard_created_immutable BEFORE UPDATE ON public.webhook_delivery_attempt FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: webhook_endpoint trg_webhook_endpoint_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_webhook_endpoint_guard_created_immutable BEFORE UPDATE ON public.webhook_endpoint FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: webhook_event trg_webhook_event_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_webhook_event_guard_created_immutable BEFORE UPDATE ON public.webhook_event FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: webhook_event_type trg_webhook_event_type_guard_created_immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_webhook_event_type_guard_created_immutable BEFORE UPDATE ON public.webhook_event_type FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();


--
-- Name: webhook_event_type trg_webhook_event_type_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_webhook_event_type_set_updated_at BEFORE UPDATE ON public.webhook_event_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: address_type address_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_type
    ADD CONSTRAINT address_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: app_service app_service_category_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service
    ADD CONSTRAINT app_service_category_code_fkey FOREIGN KEY (category_code) REFERENCES public.app_service_category(code);


--
-- Name: app_service app_service_provider_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service
    ADD CONSTRAINT app_service_provider_code_fkey FOREIGN KEY (provider_code) REFERENCES public.app_service_provider(code);


--
-- Name: app_service app_service_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service
    ADD CONSTRAINT app_service_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: auth_api_token auth_api_token_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_api_token
    ADD CONSTRAINT auth_api_token_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: auth_api_token auth_api_token_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_api_token
    ADD CONSTRAINT auth_api_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: auth_email_verification auth_email_verification_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_email_verification
    ADD CONSTRAINT auth_email_verification_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: auth_email_verification auth_email_verification_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_email_verification
    ADD CONSTRAINT auth_email_verification_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: auth_jwk auth_jwk_jwk_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_jwk
    ADD CONSTRAINT auth_jwk_jwk_status_id_fkey FOREIGN KEY (jwk_status_id) REFERENCES public.jwk_status(id);


--
-- Name: auth_jwk auth_jwk_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_jwk
    ADD CONSTRAINT auth_jwk_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: auth_mfa_otp auth_mfa_otp_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_mfa_otp
    ADD CONSTRAINT auth_mfa_otp_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: auth_mfa_otp auth_mfa_otp_user_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_mfa_otp
    ADD CONSTRAINT auth_mfa_otp_user_endpoint_id_fkey FOREIGN KEY (user_endpoint_id) REFERENCES public.user_endpoint(id);


--
-- Name: auth_mfa_otp auth_mfa_otp_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_mfa_otp
    ADD CONSTRAINT auth_mfa_otp_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: auth_password_history auth_password_history_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_history
    ADD CONSTRAINT auth_password_history_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: auth_password_history auth_password_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_history
    ADD CONSTRAINT auth_password_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: auth_password_reset auth_password_reset_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_reset
    ADD CONSTRAINT auth_password_reset_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: auth_password_reset auth_password_reset_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_reset
    ADD CONSTRAINT auth_password_reset_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: auth_refresh_token auth_refresh_token_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_token
    ADD CONSTRAINT auth_refresh_token_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.user_session_metadata(session_id);


--
-- Name: auth_refresh_token auth_refresh_token_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_token
    ADD CONSTRAINT auth_refresh_token_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: auth_refresh_token auth_refresh_token_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_token
    ADD CONSTRAINT auth_refresh_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: carrier_fee_schedule carrier_fee_schedule_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_fee_schedule
    ADD CONSTRAINT carrier_fee_schedule_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: carrier_fee_schedule carrier_fee_schedule_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_fee_schedule
    ADD CONSTRAINT carrier_fee_schedule_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order_attachment change_order_attachment_change_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_attachment
    ADD CONSTRAINT change_order_attachment_change_order_id_fkey FOREIGN KEY (change_order_id) REFERENCES public.change_order(id) ON DELETE RESTRICT;


--
-- Name: change_order change_order_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order
    ADD CONSTRAINT change_order_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: change_order_line change_order_line_change_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_change_order_id_fkey FOREIGN KEY (change_order_id) REFERENCES public.change_order(id) ON DELETE RESTRICT;


--
-- Name: change_order_line change_order_line_pricebook_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_pricebook_item_id_fkey FOREIGN KEY (pricebook_item_id) REFERENCES public.pricebook_item(id);


--
-- Name: change_order_line change_order_line_qco_line_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_qco_line_type_id_fkey FOREIGN KEY (qco_line_type_id) REFERENCES public.qco_line_type(id);


--
-- Name: change_order_line change_order_line_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(id);


--
-- Name: change_order_line change_order_line_supplier_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_supplier_item_id_fkey FOREIGN KEY (supplier_item_id) REFERENCES public.supplier_item(id);


--
-- Name: change_order_line_tax_component change_order_line_tax_component_change_order_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line_tax_component
    ADD CONSTRAINT change_order_line_tax_component_change_order_line_id_fkey FOREIGN KEY (change_order_line_id) REFERENCES public.change_order_line(id);


--
-- Name: change_order_line_tax_component change_order_line_tax_component_tax_rate_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line_tax_component
    ADD CONSTRAINT change_order_line_tax_component_tax_rate_version_id_fkey FOREIGN KEY (tax_rate_version_id) REFERENCES public.tax_rate_version(id);


--
-- Name: change_order_line change_order_line_taxability_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT change_order_line_taxability_code_fkey FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code);


--
-- Name: communication_template communication_template_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_template
    ADD CONSTRAINT communication_template_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: communication_template communication_template_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_template
    ADD CONSTRAINT communication_template_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: communication_template communication_template_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_template
    ADD CONSTRAINT communication_template_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: connector_config connector_config_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_config
    ADD CONSTRAINT connector_config_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(id);


--
-- Name: connector_run_log connector_run_log_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_run_log
    ADD CONSTRAINT connector_run_log_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(id);


--
-- Name: contact contact_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact
    ADD CONSTRAINT contact_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: contact_endpoint contact_endpoint_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_endpoint
    ADD CONSTRAINT contact_endpoint_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: contact_portal_invite contact_portal_invite_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_portal_invite
    ADD CONSTRAINT contact_portal_invite_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: contact_portal_invite contact_portal_invite_invited_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_portal_invite
    ADD CONSTRAINT contact_portal_invite_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES public."user"(id);


--
-- Name: contact_type contact_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_type
    ADD CONSTRAINT contact_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: conversation_message conversation_message_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message
    ADD CONSTRAINT conversation_message_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id);


--
-- Name: conversation_message conversation_message_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message
    ADD CONSTRAINT conversation_message_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.conversation_session(id);


--
-- Name: conversation_session conversation_session_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_session
    ADD CONSTRAINT conversation_session_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: conversation_session conversation_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_session
    ADD CONSTRAINT conversation_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: customer_communication customer_communication_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication customer_communication_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: customer_communication customer_communication_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE SET NULL;


--
-- Name: customer_communication_message customer_communication_message_audit_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message
    ADD CONSTRAINT customer_communication_message_audit_user_id_fkey FOREIGN KEY (audit_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_message_read_state customer_communication_message_read_state_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message_read_state
    ADD CONSTRAINT customer_communication_message_read_state_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.customer_communication_message(id) ON DELETE CASCADE;


--
-- Name: customer_communication_message_read_state customer_communication_message_read_state_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message_read_state
    ADD CONSTRAINT customer_communication_message_read_state_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: customer_communication_message customer_communication_message_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message
    ADD CONSTRAINT customer_communication_message_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.communication_template(id) ON DELETE SET NULL;


--
-- Name: customer_communication_message customer_communication_message_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message
    ADD CONSTRAINT customer_communication_message_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.customer_communication_thread(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_message customer_communication_message_voice_audio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_message
    ADD CONSTRAINT customer_communication_message_voice_audio_id_fkey FOREIGN KEY (voice_audio_id) REFERENCES public.voice_command_log(id) ON DELETE SET NULL;


--
-- Name: customer_communication customer_communication_notification_outbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_notification_outbox_id_fkey FOREIGN KEY (notification_outbox_id) REFERENCES public.notification_outbox(id) ON DELETE SET NULL;


--
-- Name: customer_communication customer_communication_sender_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_sender_user_id_fkey FOREIGN KEY (sender_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication customer_communication_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.communication_template(id) ON DELETE SET NULL;


--
-- Name: customer_communication customer_communication_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_thread customer_communication_thread_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_thread customer_communication_thread_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: customer_communication customer_communication_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.customer_communication_thread(id) ON DELETE SET NULL;


--
-- Name: customer_communication_thread customer_communication_thread_tech_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_tech_id_fkey FOREIGN KEY (tech_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_thread customer_communication_thread_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_thread customer_communication_thread_tenant_phone_number_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_tenant_phone_number_id_fkey FOREIGN KEY (tenant_phone_number_id) REFERENCES public.tenant_phone_number(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_thread customer_communication_thread_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_thread
    ADD CONSTRAINT customer_communication_thread_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication_unrouted customer_communication_unrouted_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_unrouted
    ADD CONSTRAINT customer_communication_unrouted_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: customer_communication_unrouted customer_communication_unrouted_resolved_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_unrouted
    ADD CONSTRAINT customer_communication_unrouted_resolved_thread_id_fkey FOREIGN KEY (resolved_thread_id) REFERENCES public.customer_communication_thread(id) ON DELETE SET NULL;


--
-- Name: customer_communication_unrouted customer_communication_unrouted_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication_unrouted
    ADD CONSTRAINT customer_communication_unrouted_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: customer_communication customer_communication_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT customer_communication_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer customer_last_assigned_tech_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT customer_last_assigned_tech_id_fkey FOREIGN KEY (last_assigned_tech_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: customer customer_lifecycle_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT customer_lifecycle_status_id_fkey FOREIGN KEY (lifecycle_status_id) REFERENCES public.customer_lifecycle_status(id);


--
-- Name: customer_lifecycle_status customer_lifecycle_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_lifecycle_status
    ADD CONSTRAINT customer_lifecycle_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: customer customer_sms_consent_attested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT customer_sms_consent_attested_by_fkey FOREIGN KEY (sms_consent_attested_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_sms_consent_audit customer_sms_consent_audit_attested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sms_consent_audit
    ADD CONSTRAINT customer_sms_consent_audit_attested_by_fkey FOREIGN KEY (attested_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_sms_consent_audit customer_sms_consent_audit_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sms_consent_audit
    ADD CONSTRAINT customer_sms_consent_audit_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_sms_consent_audit customer_sms_consent_audit_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sms_consent_audit
    ADD CONSTRAINT customer_sms_consent_audit_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: customer_sms_consent_audit customer_sms_consent_audit_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sms_consent_audit
    ADD CONSTRAINT customer_sms_consent_audit_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: customer customer_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT customer_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: data_export_request data_export_request_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_export_request
    ADD CONSTRAINT data_export_request_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: data_export_request data_export_request_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_export_request
    ADD CONSTRAINT data_export_request_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: discount_version discount_version_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_version
    ADD CONSTRAINT discount_version_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: entity_address entity_address_address_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT entity_address_address_id_fkey FOREIGN KEY (address_id) REFERENCES public.address(id);


--
-- Name: entity_address entity_address_address_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT entity_address_address_type_code_fkey FOREIGN KEY (address_type_code) REFERENCES public.address_type(code);


--
-- Name: entity_address entity_address_entity_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT entity_address_entity_type_code_fkey FOREIGN KEY (entity_type_code) REFERENCES public.entity_type(code);


--
-- Name: entity_contact entity_contact_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT entity_contact_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: entity_contact entity_contact_contact_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT entity_contact_contact_type_code_fkey FOREIGN KEY (contact_type_code) REFERENCES public.contact_type(code);


--
-- Name: entity_contact entity_contact_entity_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT entity_contact_entity_type_code_fkey FOREIGN KEY (entity_type_code) REFERENCES public.entity_type(code);


--
-- Name: address fk_address_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address
    ADD CONSTRAINT fk_address_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: address fk_address_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address
    ADD CONSTRAINT fk_address_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: address_type fk_address_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_type
    ADD CONSTRAINT fk_address_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: address_type fk_address_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_type
    ADD CONSTRAINT fk_address_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: address fk_address_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address
    ADD CONSTRAINT fk_address_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: app_service_category fk_app_service_category_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service_category
    ADD CONSTRAINT fk_app_service_category_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: app_service_category fk_app_service_category_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service_category
    ADD CONSTRAINT fk_app_service_category_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: app_service fk_app_service_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service
    ADD CONSTRAINT fk_app_service_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: app_service_provider fk_app_service_provider_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service_provider
    ADD CONSTRAINT fk_app_service_provider_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: app_service_provider fk_app_service_provider_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service_provider
    ADD CONSTRAINT fk_app_service_provider_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: app_service fk_app_service_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_service
    ADD CONSTRAINT fk_app_service_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: auth_api_token fk_auth_api_token_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_api_token
    ADD CONSTRAINT fk_auth_api_token_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: auth_email_verification fk_auth_email_verification_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_email_verification
    ADD CONSTRAINT fk_auth_email_verification_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: auth_jwk fk_auth_jwk_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_jwk
    ADD CONSTRAINT fk_auth_jwk_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: auth_mfa_otp fk_auth_mfa_otp_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_mfa_otp
    ADD CONSTRAINT fk_auth_mfa_otp_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: auth_password_history fk_auth_password_history_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_history
    ADD CONSTRAINT fk_auth_password_history_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: auth_password_reset fk_auth_password_reset_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_password_reset
    ADD CONSTRAINT fk_auth_password_reset_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order_attachment fk_change_order_attachment_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_attachment
    ADD CONSTRAINT fk_change_order_attachment_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order_attachment fk_change_order_attachment_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_attachment
    ADD CONSTRAINT fk_change_order_attachment_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: change_order_attachment fk_change_order_attachment_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_attachment
    ADD CONSTRAINT fk_change_order_attachment_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order fk_change_order_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order
    ADD CONSTRAINT fk_change_order_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order_line fk_change_order_line_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT fk_change_order_line_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order_line_tax_component fk_change_order_line_tax_component_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line_tax_component
    ADD CONSTRAINT fk_change_order_line_tax_component_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order_line_tax_component fk_change_order_line_tax_component_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line_tax_component
    ADD CONSTRAINT fk_change_order_line_tax_component_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: change_order_line fk_change_order_line_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT fk_change_order_line_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: change_order_line fk_change_order_line_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order_line
    ADD CONSTRAINT fk_change_order_line_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: change_order fk_change_order_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order
    ADD CONSTRAINT fk_change_order_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: change_order fk_change_order_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_order
    ADD CONSTRAINT fk_change_order_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_communication fk_comm_template_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_communication
    ADD CONSTRAINT fk_comm_template_type FOREIGN KEY (template_code) REFERENCES public.customer_comm_template_type(code) ON DELETE RESTRICT;


--
-- Name: communication_template fk_communication_template_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_template
    ADD CONSTRAINT fk_communication_template_type FOREIGN KEY (template_code) REFERENCES public.customer_comm_template_type(code) ON DELETE RESTRICT;


--
-- Name: connector_config fk_connector_config_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_config
    ADD CONSTRAINT fk_connector_config_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: connector_config fk_connector_config_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_config
    ADD CONSTRAINT fk_connector_config_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact fk_contact_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact
    ADD CONSTRAINT fk_contact_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact_endpoint fk_contact_endpoint_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_endpoint
    ADD CONSTRAINT fk_contact_endpoint_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact_endpoint fk_contact_endpoint_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_endpoint
    ADD CONSTRAINT fk_contact_endpoint_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: contact_endpoint fk_contact_endpoint_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_endpoint
    ADD CONSTRAINT fk_contact_endpoint_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact_portal_invite fk_contact_portal_invite_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_portal_invite
    ADD CONSTRAINT fk_contact_portal_invite_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact_portal_invite fk_contact_portal_invite_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_portal_invite
    ADD CONSTRAINT fk_contact_portal_invite_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: contact fk_contact_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact
    ADD CONSTRAINT fk_contact_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: contact_type fk_contact_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_type
    ADD CONSTRAINT fk_contact_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact_type fk_contact_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_type
    ADD CONSTRAINT fk_contact_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: contact fk_contact_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact
    ADD CONSTRAINT fk_contact_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: conversation_message fk_conversation_message_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message
    ADD CONSTRAINT fk_conversation_message_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: conversation_session fk_conversation_session_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_session
    ADD CONSTRAINT fk_conversation_session_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: conversation_session fk_conversation_session_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_session
    ADD CONSTRAINT fk_conversation_session_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: calendar_sync_conflict fk_csc_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT fk_csc_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: calendar_sync_conflict fk_csc_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT fk_csc_job FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: calendar_sync_conflict fk_csc_pilot_modified_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT fk_csc_pilot_modified_by FOREIGN KEY (pilot_modified_by_user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: calendar_sync_conflict fk_csc_resolved_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT fk_csc_resolved_by FOREIGN KEY (resolved_by_user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: calendar_sync_conflict fk_csc_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT fk_csc_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: calendar_sync_conflict fk_csc_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_conflict
    ADD CONSTRAINT fk_csc_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: calendar_sync_log fk_csl_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_log
    ADD CONSTRAINT fk_csl_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: calendar_sync_log fk_csl_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_sync_log
    ADD CONSTRAINT fk_csl_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: currency fk_currency_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency
    ADD CONSTRAINT fk_currency_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: currency fk_currency_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency
    ADD CONSTRAINT fk_currency_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_comm_template_type fk_customer_comm_template_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_comm_template_type
    ADD CONSTRAINT fk_customer_comm_template_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_comm_template_type fk_customer_comm_template_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_comm_template_type
    ADD CONSTRAINT fk_customer_comm_template_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer fk_customer_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT fk_customer_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_lifecycle_status fk_customer_lifecycle_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_lifecycle_status
    ADD CONSTRAINT fk_customer_lifecycle_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer_lifecycle_status fk_customer_lifecycle_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_lifecycle_status
    ADD CONSTRAINT fk_customer_lifecycle_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: customer fk_customer_taxability_code; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT fk_customer_taxability_code FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code) ON DELETE RESTRICT;


--
-- Name: customer fk_customer_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT fk_customer_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: discount_version fk_discount_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_version
    ADD CONSTRAINT fk_discount_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: email_template fk_email_template_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_template
    ADD CONSTRAINT fk_email_template_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: email_template fk_email_template_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_template
    ADD CONSTRAINT fk_email_template_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: entity_address fk_entity_address_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT fk_entity_address_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: entity_address fk_entity_address_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT fk_entity_address_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: entity_address fk_entity_address_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_address
    ADD CONSTRAINT fk_entity_address_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: entity_contact fk_entity_contact_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT fk_entity_contact_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: entity_contact fk_entity_contact_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT fk_entity_contact_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: entity_contact fk_entity_contact_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_contact
    ADD CONSTRAINT fk_entity_contact_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: entity_type fk_entity_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type
    ADD CONSTRAINT fk_entity_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: entity_type fk_entity_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_type
    ADD CONSTRAINT fk_entity_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: feedback_submission fk_feedback_submission_session_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback_submission
    ADD CONSTRAINT fk_feedback_submission_session_id FOREIGN KEY (from_help_chat_session_id) REFERENCES public.help_chat_session(id) ON DELETE SET NULL;


--
-- Name: feedback_submission fk_feedback_submission_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback_submission
    ADD CONSTRAINT fk_feedback_submission_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: feedback_submission fk_feedback_submission_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback_submission
    ADD CONSTRAINT fk_feedback_submission_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: help_article_chunk fk_help_article_chunk_article_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_article_chunk
    ADD CONSTRAINT fk_help_article_chunk_article_id FOREIGN KEY (article_id) REFERENCES public.help_article(code) ON DELETE CASCADE;


--
-- Name: help_chat_message fk_help_chat_message_session_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_chat_message
    ADD CONSTRAINT fk_help_chat_message_session_id FOREIGN KEY (session_id) REFERENCES public.help_chat_session(id) ON DELETE CASCADE;


--
-- Name: help_chat_message fk_help_chat_message_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_chat_message
    ADD CONSTRAINT fk_help_chat_message_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: help_chat_session fk_help_chat_session_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_chat_session
    ADD CONSTRAINT fk_help_chat_session_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: help_chat_session fk_help_chat_session_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_chat_session
    ADD CONSTRAINT fk_help_chat_session_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: in_app_notification fk_in_app_notif_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notification
    ADD CONSTRAINT fk_in_app_notif_category FOREIGN KEY (category_id) REFERENCES public.notification_category(code) ON DELETE RESTRICT;


--
-- Name: in_app_notification fk_in_app_notif_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notification
    ADD CONSTRAINT fk_in_app_notif_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: in_app_notification fk_in_app_notif_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notification
    ADD CONSTRAINT fk_in_app_notif_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_credential fk_integration_credential_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credential
    ADD CONSTRAINT fk_integration_credential_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_credential fk_integration_credential_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credential
    ADD CONSTRAINT fk_integration_credential_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_sync_conflict fk_integration_sync_conflict_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT fk_integration_sync_conflict_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_sync_conflict fk_integration_sync_conflict_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT fk_integration_sync_conflict_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_sync_mapping fk_integration_sync_mapping_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT fk_integration_sync_mapping_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_sync_mapping fk_integration_sync_mapping_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT fk_integration_sync_mapping_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice fk_invoice_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT fk_invoice_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_line fk_invoice_line_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT fk_invoice_line_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_line_tax_component fk_invoice_line_tax_component_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_tax_component
    ADD CONSTRAINT fk_invoice_line_tax_component_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_line_tax_component fk_invoice_line_tax_component_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_tax_component
    ADD CONSTRAINT fk_invoice_line_tax_component_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: invoice_line fk_invoice_line_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT fk_invoice_line_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: invoice_public_link fk_invoice_public_link_contact; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT fk_invoice_public_link_contact FOREIGN KEY (contact_id) REFERENCES public.contact(id) ON DELETE RESTRICT;


--
-- Name: invoice_public_link fk_invoice_public_link_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT fk_invoice_public_link_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_public_link fk_invoice_public_link_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT fk_invoice_public_link_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_public_link fk_invoice_public_link_invoice; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT fk_invoice_public_link_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoice(id) ON DELETE RESTRICT;


--
-- Name: invoice_public_link fk_invoice_public_link_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT fk_invoice_public_link_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: invoice_public_link fk_invoice_public_link_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_public_link
    ADD CONSTRAINT fk_invoice_public_link_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_status fk_invoice_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_status
    ADD CONSTRAINT fk_invoice_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice_status fk_invoice_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_status
    ADD CONSTRAINT fk_invoice_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: invoice fk_invoice_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT fk_invoice_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_attachment fk_job_attachment_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_attachment
    ADD CONSTRAINT fk_job_attachment_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_attachment fk_job_attachment_expense; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_attachment
    ADD CONSTRAINT fk_job_attachment_expense FOREIGN KEY (expense_id) REFERENCES public.job_expense(id) ON DELETE SET NULL;


--
-- Name: job_attachment fk_job_attachment_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_attachment
    ADD CONSTRAINT fk_job_attachment_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job fk_job_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT fk_job_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_expense_category fk_job_expense_category_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense_category
    ADD CONSTRAINT fk_job_expense_category_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_expense_category fk_job_expense_category_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense_category
    ADD CONSTRAINT fk_job_expense_category_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_expense fk_job_expense_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT fk_job_expense_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_expense fk_job_expense_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT fk_job_expense_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_expense fk_job_expense_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT fk_job_expense_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_notes fk_job_notes_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_notes
    ADD CONSTRAINT fk_job_notes_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_notes fk_job_notes_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_notes
    ADD CONSTRAINT fk_job_notes_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job_notes fk_job_notes_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_notes
    ADD CONSTRAINT fk_job_notes_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_status fk_job_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_status
    ADD CONSTRAINT fk_job_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_status fk_job_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_status
    ADD CONSTRAINT fk_job_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_time_entry fk_job_time_entry_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT fk_job_time_entry_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_time_entry fk_job_time_entry_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT fk_job_time_entry_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job_time_entry fk_job_time_entry_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT fk_job_time_entry_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job fk_job_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT fk_job_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_tech_assignment fk_jta_assigned_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT fk_jta_assigned_by FOREIGN KEY (assigned_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_tech_assignment fk_jta_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT fk_jta_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: job_tech_assignment fk_jta_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT fk_jta_job FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: job_tech_assignment fk_jta_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT fk_jta_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job_tech_assignment fk_jta_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT fk_jta_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: job_tech_assignment fk_jta_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_tech_assignment
    ADD CONSTRAINT fk_jta_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_time_entry fk_jte_quote_line; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT fk_jte_quote_line FOREIGN KEY (quote_line_id) REFERENCES public.quote_line(id) ON DELETE RESTRICT;


--
-- Name: jwk_status fk_jwk_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jwk_status
    ADD CONSTRAINT fk_jwk_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: labor_rate_version fk_labor_rate_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.labor_rate_version
    ADD CONSTRAINT fk_labor_rate_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: labor_rate_version fk_labor_rate_version_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.labor_rate_version
    ADD CONSTRAINT fk_labor_rate_version_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_owner_escalation fk_mobile_sync_escalation_conflict; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT fk_mobile_sync_escalation_conflict FOREIGN KEY (conflict_id) REFERENCES public.mobile_sync_event(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_owner_escalation fk_mobile_sync_escalation_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT fk_mobile_sync_escalation_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_owner_escalation fk_mobile_sync_escalation_originating_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT fk_mobile_sync_escalation_originating_user FOREIGN KEY (originating_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_owner_escalation fk_mobile_sync_escalation_resolved_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT fk_mobile_sync_escalation_resolved_by FOREIGN KEY (resolved_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_owner_escalation fk_mobile_sync_escalation_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT fk_mobile_sync_escalation_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_owner_escalation fk_mobile_sync_escalation_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_owner_escalation
    ADD CONSTRAINT fk_mobile_sync_escalation_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_event fk_mobile_sync_event_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event
    ADD CONSTRAINT fk_mobile_sync_event_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_event fk_mobile_sync_event_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event
    ADD CONSTRAINT fk_mobile_sync_event_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_default_policy fk_notif_default_policy_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_default_policy
    ADD CONSTRAINT fk_notif_default_policy_category FOREIGN KEY (category_id) REFERENCES public.notification_category(code) ON DELETE RESTRICT;


--
-- Name: notification_outbox fk_notif_outbox_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT fk_notif_outbox_category FOREIGN KEY (category_id) REFERENCES public.notification_category(code);


--
-- Name: notification_outbox fk_notif_outbox_sub_trigger; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT fk_notif_outbox_sub_trigger FOREIGN KEY (sub_trigger_id) REFERENCES public.notification_category_sub_trigger(code);


--
-- Name: notification_preference fk_notif_pref_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preference
    ADD CONSTRAINT fk_notif_pref_category FOREIGN KEY (category_id) REFERENCES public.notification_category(code) ON DELETE RESTRICT;


--
-- Name: notification_preference fk_notif_pref_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preference
    ADD CONSTRAINT fk_notif_pref_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: notification_preference fk_notif_pref_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preference
    ADD CONSTRAINT fk_notif_pref_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_category_sub_trigger fk_notif_sub_trigger_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category_sub_trigger
    ADD CONSTRAINT fk_notif_sub_trigger_category FOREIGN KEY (category_id) REFERENCES public.notification_category(code) ON DELETE RESTRICT;


--
-- Name: notification_channel fk_notification_channel_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_channel
    ADD CONSTRAINT fk_notification_channel_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_channel fk_notification_channel_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_channel
    ADD CONSTRAINT fk_notification_channel_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_event fk_notification_event_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_event
    ADD CONSTRAINT fk_notification_event_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_outbox fk_notification_outbox_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT fk_notification_outbox_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_outbox fk_notification_outbox_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT fk_notification_outbox_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_template fk_notification_template_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_template
    ADD CONSTRAINT fk_notification_template_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_template fk_notification_template_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_template
    ADD CONSTRAINT fk_notification_template_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_type fk_notification_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_type
    ADD CONSTRAINT fk_notification_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_type fk_notification_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_type
    ADD CONSTRAINT fk_notification_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_outbox fk_outbox_channel; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT fk_outbox_channel FOREIGN KEY (channel) REFERENCES public.notification_channel(code) ON DELETE RESTRICT;


--
-- Name: password_policy fk_password_policy_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_policy
    ADD CONSTRAINT fk_password_policy_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: password_policy fk_password_policy_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_policy
    ADD CONSTRAINT fk_password_policy_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment fk_payment_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT fk_payment_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_method fk_payment_method_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT fk_payment_method_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_method fk_payment_method_customer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT fk_payment_method_customer_id FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: payment_method fk_payment_method_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT fk_payment_method_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_status fk_payment_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_status
    ADD CONSTRAINT fk_payment_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_status fk_payment_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_status
    ADD CONSTRAINT fk_payment_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_type fk_payment_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_type
    ADD CONSTRAINT fk_payment_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_type fk_payment_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_type
    ADD CONSTRAINT fk_payment_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment fk_payment_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT fk_payment_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: platform_role fk_platform_role_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_role
    ADD CONSTRAINT fk_platform_role_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: platform_role fk_platform_role_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_role
    ADD CONSTRAINT fk_platform_role_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: pricebook_item fk_pricebook_item_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT fk_pricebook_item_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: pricebook_item fk_pricebook_item_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT fk_pricebook_item_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: pricebook_item_version fk_pricebook_item_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item_version
    ADD CONSTRAINT fk_pricebook_item_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: pricing_cache fk_pricing_cache_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache
    ADD CONSTRAINT fk_pricing_cache_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: product_feature fk_product_feature_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_feature
    ADD CONSTRAINT fk_product_feature_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: product_feature fk_product_feature_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_feature
    ADD CONSTRAINT fk_product_feature_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: product_plan fk_product_plan_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan
    ADD CONSTRAINT fk_product_plan_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: product_plan_product_feature_version fk_product_plan_product_feature_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_product_feature_version
    ADD CONSTRAINT fk_product_plan_product_feature_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: product_plan fk_product_plan_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan
    ADD CONSTRAINT fk_product_plan_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: product_plan_version fk_product_plan_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_version
    ADD CONSTRAINT fk_product_plan_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: psp_customer fk_psp_customer_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_customer
    ADD CONSTRAINT fk_psp_customer_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: psp_customer fk_psp_customer_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_customer
    ADD CONSTRAINT fk_psp_customer_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: psp_transaction_log fk_psp_transaction_log_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_transaction_log
    ADD CONSTRAINT fk_psp_transaction_log_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: public_link_short_code fk_public_link_short_code_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.public_link_short_code
    ADD CONSTRAINT fk_public_link_short_code_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: qco_line_type fk_qco_line_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qco_line_type
    ADD CONSTRAINT fk_qco_line_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: qco_line_type fk_qco_line_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qco_line_type
    ADD CONSTRAINT fk_qco_line_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: qpl_contact_action_type fk_qpl_contact_action_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qpl_contact_action_type
    ADD CONSTRAINT fk_qpl_contact_action_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: qpl_contact_action_type fk_qpl_contact_action_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qpl_contact_action_type
    ADD CONSTRAINT fk_qpl_contact_action_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_template_version fk_qtv_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_version
    ADD CONSTRAINT fk_qtv_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_template_version fk_qtv_template_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_version
    ADD CONSTRAINT fk_qtv_template_id FOREIGN KEY (template_id) REFERENCES public.quote_template(id) ON DELETE RESTRICT;


--
-- Name: quote_acceptance fk_quote_acceptance_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT fk_quote_acceptance_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_acceptance fk_quote_acceptance_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT fk_quote_acceptance_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_approval_comment fk_quote_approval_comment_author; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT fk_quote_approval_comment_author FOREIGN KEY (author_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_approval_comment fk_quote_approval_comment_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT fk_quote_approval_comment_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_approval_comment fk_quote_approval_comment_quote; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT fk_quote_approval_comment_quote FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: quote_approval_comment fk_quote_approval_comment_target_line; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT fk_quote_approval_comment_target_line FOREIGN KEY (target_line_id) REFERENCES public.quote_line(id) ON DELETE RESTRICT;


--
-- Name: quote_approval_comment fk_quote_approval_comment_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT fk_quote_approval_comment_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_approval_comment fk_quote_approval_comment_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_approval_comment
    ADD CONSTRAINT fk_quote_approval_comment_version FOREIGN KEY (quote_version_id) REFERENCES public.quote_version(id) ON DELETE RESTRICT;


--
-- Name: quote fk_quote_approved_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT fk_quote_approved_by_user_id FOREIGN KEY (approved_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote fk_quote_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT fk_quote_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote fk_quote_discount_applied_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT fk_quote_discount_applied_by_user_id FOREIGN KEY (discount_applied_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_line fk_quote_line_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT fk_quote_line_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_line fk_quote_line_parent_line_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT fk_quote_line_parent_line_id FOREIGN KEY (parent_line_id) REFERENCES public.quote_line(id) ON DELETE RESTRICT;


--
-- Name: quote_line_tax_component fk_quote_line_tax_component_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line_tax_component
    ADD CONSTRAINT fk_quote_line_tax_component_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_line_tax_component fk_quote_line_tax_component_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line_tax_component
    ADD CONSTRAINT fk_quote_line_tax_component_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_line fk_quote_line_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT fk_quote_line_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_line fk_quote_line_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT fk_quote_line_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_link_status fk_quote_link_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_link_status
    ADD CONSTRAINT fk_quote_link_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_link_status fk_quote_link_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_link_status
    ADD CONSTRAINT fk_quote_link_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_message fk_quote_message_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_message
    ADD CONSTRAINT fk_quote_message_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_message fk_quote_message_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_message
    ADD CONSTRAINT fk_quote_message_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_editor; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_editor FOREIGN KEY (editor_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_quote; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_quote FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_target_line; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_target_line FOREIGN KEY (target_line_id) REFERENCES public.quote_line(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_pending_edit fk_quote_pending_edit_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_pending_edit
    ADD CONSTRAINT fk_quote_pending_edit_version FOREIGN KEY (quote_version_id) REFERENCES public.quote_version(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link_contact_action fk_quote_public_link_contact_action_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT fk_quote_public_link_contact_action_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link_contact_action fk_quote_public_link_contact_action_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT fk_quote_public_link_contact_action_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link fk_quote_public_link_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT fk_quote_public_link_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link fk_quote_public_link_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT fk_quote_public_link_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link fk_quote_public_link_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT fk_quote_public_link_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link fk_quote_public_link_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT fk_quote_public_link_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_status fk_quote_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_status
    ADD CONSTRAINT fk_quote_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_status fk_quote_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_status
    ADD CONSTRAINT fk_quote_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote fk_quote_submitted_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT fk_quote_submitted_by_user_id FOREIGN KEY (submitted_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_template fk_quote_template_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template
    ADD CONSTRAINT fk_quote_template_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_template_line fk_quote_template_line_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT fk_quote_template_line_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_template_line fk_quote_template_line_parent; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT fk_quote_template_line_parent FOREIGN KEY (parent_line_id) REFERENCES public.quote_template_line(id) ON DELETE RESTRICT;


--
-- Name: quote_template_line fk_quote_template_line_qco_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT fk_quote_template_line_qco_type FOREIGN KEY (qco_line_type_id) REFERENCES public.qco_line_type(id);


--
-- Name: quote_template_line fk_quote_template_line_template; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT fk_quote_template_line_template FOREIGN KEY (quote_template_id) REFERENCES public.quote_template(id) ON DELETE RESTRICT;


--
-- Name: quote_template_line fk_quote_template_line_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT fk_quote_template_line_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_template_line fk_quote_template_line_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template_line
    ADD CONSTRAINT fk_quote_template_line_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_template fk_quote_template_system_template_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template
    ADD CONSTRAINT fk_quote_template_system_template_id FOREIGN KEY (system_template_id) REFERENCES public.quote_template(id) ON DELETE RESTRICT;


--
-- Name: quote_template fk_quote_template_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template
    ADD CONSTRAINT fk_quote_template_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_template fk_quote_template_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_template
    ADD CONSTRAINT fk_quote_template_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote fk_quote_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT fk_quote_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_version fk_quote_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_version
    ADD CONSTRAINT fk_quote_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: quote_version fk_quote_version_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_version
    ADD CONSTRAINT fk_quote_version_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: site fk_site_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site
    ADD CONSTRAINT fk_site_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: site_lifecycle_status fk_site_lifecycle_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_lifecycle_status
    ADD CONSTRAINT fk_site_lifecycle_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: site_lifecycle_status fk_site_lifecycle_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_lifecycle_status
    ADD CONSTRAINT fk_site_lifecycle_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: site fk_site_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site
    ADD CONSTRAINT fk_site_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: sso_provider fk_sso_provider_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_provider
    ADD CONSTRAINT fk_sso_provider_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: sso_provider fk_sso_provider_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_provider
    ADD CONSTRAINT fk_sso_provider_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription fk_subscription_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT fk_subscription_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription_status fk_subscription_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_status
    ADD CONSTRAINT fk_subscription_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription_status fk_subscription_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_status
    ADD CONSTRAINT fk_subscription_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription fk_subscription_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT fk_subscription_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription_usage fk_subscription_usage_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT fk_subscription_usage_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription_usage fk_subscription_usage_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT fk_subscription_usage_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: subscription_usage fk_subscription_usage_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT fk_subscription_usage_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier fk_supplier_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier
    ADD CONSTRAINT fk_supplier_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item_category fk_supplier_item_category_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_category
    ADD CONSTRAINT fk_supplier_item_category_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item_category fk_supplier_item_category_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_category
    ADD CONSTRAINT fk_supplier_item_category_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item fk_supplier_item_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT fk_supplier_item_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item_price fk_supplier_item_price_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price
    ADD CONSTRAINT fk_supplier_item_price_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item_uom fk_supplier_item_uom_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_uom
    ADD CONSTRAINT fk_supplier_item_uom_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item_uom fk_supplier_item_uom_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_uom
    ADD CONSTRAINT fk_supplier_item_uom_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_item fk_supplier_item_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT fk_supplier_item_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_lifecycle_status fk_supplier_lifecycle_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_lifecycle_status
    ADD CONSTRAINT fk_supplier_lifecycle_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier_lifecycle_status fk_supplier_lifecycle_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_lifecycle_status
    ADD CONSTRAINT fk_supplier_lifecycle_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: supplier fk_supplier_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier
    ADD CONSTRAINT fk_supplier_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: sync_conflict_classification_matrix fk_sync_conflict_matrix_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_conflict_classification_matrix
    ADD CONSTRAINT fk_sync_conflict_matrix_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: sync_conflict_classification_matrix fk_sync_conflict_matrix_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_conflict_classification_matrix
    ADD CONSTRAINT fk_sync_conflict_matrix_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: sync_conflict_classification_matrix fk_sync_conflict_matrix_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_conflict_classification_matrix
    ADD CONSTRAINT fk_sync_conflict_matrix_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tech_availability fk_ta_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tech_availability
    ADD CONSTRAINT fk_ta_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: tech_availability fk_ta_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tech_availability
    ADD CONSTRAINT fk_ta_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tech_availability fk_ta_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tech_availability
    ADD CONSTRAINT fk_ta_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: tech_availability fk_ta_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tech_availability
    ADD CONSTRAINT fk_ta_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tax_rate_version fk_tax_rate_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tax_rate_version
    ADD CONSTRAINT fk_tax_rate_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tax_rate_version fk_tax_rate_version_taxability_code; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tax_rate_version
    ADD CONSTRAINT fk_tax_rate_version_taxability_code FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code) ON DELETE RESTRICT;


--
-- Name: taxability_code fk_taxability_code_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.taxability_code
    ADD CONSTRAINT fk_taxability_code_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: taxability_code fk_taxability_code_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.taxability_code
    ADD CONSTRAINT fk_taxability_code_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_calendar_integration fk_tci_connected_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_calendar_integration
    ADD CONSTRAINT fk_tci_connected_by FOREIGN KEY (connected_by_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_calendar_integration fk_tci_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_calendar_integration
    ADD CONSTRAINT fk_tci_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: tenant_calendar_integration fk_tci_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_calendar_integration
    ADD CONSTRAINT fk_tci_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_calendar_integration fk_tci_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_calendar_integration
    ADD CONSTRAINT fk_tci_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: tenant fk_tenant_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT fk_tenant_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant fk_tenant_current_subscription_tier_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT fk_tenant_current_subscription_tier_id FOREIGN KEY (current_subscription_tier_id) REFERENCES public.subscription_tier(tier_id) ON DELETE RESTRICT;


--
-- Name: tenant_domain fk_tenant_domain_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_domain
    ADD CONSTRAINT fk_tenant_domain_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_domain fk_tenant_domain_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_domain
    ADD CONSTRAINT fk_tenant_domain_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_email_branding fk_tenant_email_branding_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_email_branding
    ADD CONSTRAINT fk_tenant_email_branding_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_email_branding fk_tenant_email_branding_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_email_branding
    ADD CONSTRAINT fk_tenant_email_branding_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_email_branding fk_tenant_email_branding_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_email_branding
    ADD CONSTRAINT fk_tenant_email_branding_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_legal_acceptance fk_tenant_legal_acceptance_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_legal_acceptance
    ADD CONSTRAINT fk_tenant_legal_acceptance_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_markup_version fk_tenant_markup_version_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_markup_version
    ADD CONSTRAINT fk_tenant_markup_version_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_onboarding_checklist fk_tenant_onboarding_checklist_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_onboarding_checklist
    ADD CONSTRAINT fk_tenant_onboarding_checklist_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_product_feature_override fk_tenant_product_feature_override_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_product_feature_override
    ADD CONSTRAINT fk_tenant_product_feature_override_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_product_feature_override fk_tenant_product_feature_override_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_product_feature_override
    ADD CONSTRAINT fk_tenant_product_feature_override_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_signup fk_tenant_signup_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_signup
    ADD CONSTRAINT fk_tenant_signup_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_subscription_usage fk_tenant_subscription_usage_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_subscription_usage
    ADD CONSTRAINT fk_tenant_subscription_usage_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_tier_override fk_tenant_tier_override_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_tier_override
    ADD CONSTRAINT fk_tenant_tier_override_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant fk_tenant_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT fk_tenant_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user fk_tenant_user_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT fk_tenant_user_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user_invite fk_tenant_user_invite_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_invite
    ADD CONSTRAINT fk_tenant_user_invite_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user_invite fk_tenant_user_invite_role_code; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_invite
    ADD CONSTRAINT fk_tenant_user_invite_role_code FOREIGN KEY (role_code) REFERENCES public.tenant_user_role(code);


--
-- Name: tenant_user_role fk_tenant_user_role_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_role
    ADD CONSTRAINT fk_tenant_user_role_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user_role fk_tenant_user_role_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_role
    ADD CONSTRAINT fk_tenant_user_role_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user_status fk_tenant_user_status_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_status
    ADD CONSTRAINT fk_tenant_user_status_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user_status fk_tenant_user_status_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_status
    ADD CONSTRAINT fk_tenant_user_status_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user fk_tenant_user_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT fk_tenant_user_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: usage_ledger fk_usage_ledger_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT fk_usage_ledger_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user fk_user_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT fk_user_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_dashboard_widget fk_user_dashboard_widget_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_dashboard_widget
    ADD CONSTRAINT fk_user_dashboard_widget_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_dashboard_widget fk_user_dashboard_widget_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_dashboard_widget
    ADD CONSTRAINT fk_user_dashboard_widget_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: user_dashboard_widget fk_user_dashboard_widget_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_dashboard_widget
    ADD CONSTRAINT fk_user_dashboard_widget_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_dashboard_widget fk_user_dashboard_widget_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_dashboard_widget
    ADD CONSTRAINT fk_user_dashboard_widget_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_endpoint fk_user_endpoint_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_endpoint
    ADD CONSTRAINT fk_user_endpoint_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_endpoint fk_user_endpoint_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_endpoint
    ADD CONSTRAINT fk_user_endpoint_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_preference fk_user_preference_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_preference
    ADD CONSTRAINT fk_user_preference_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_preference fk_user_preference_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_preference
    ADD CONSTRAINT fk_user_preference_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_setting_override fk_user_setting_override_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_setting_override
    ADD CONSTRAINT fk_user_setting_override_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_setting_override fk_user_setting_override_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_setting_override
    ADD CONSTRAINT fk_user_setting_override_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_setting_override fk_user_setting_override_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_setting_override
    ADD CONSTRAINT fk_user_setting_override_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_setting_override fk_user_setting_override_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_setting_override
    ADD CONSTRAINT fk_user_setting_override_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: user_sso_identity fk_user_sso_identity_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sso_identity
    ADD CONSTRAINT fk_user_sso_identity_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_sso_identity fk_user_sso_identity_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sso_identity
    ADD CONSTRAINT fk_user_sso_identity_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user fk_user_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT fk_user_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: voice_feedback fk_voice_feedback_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_feedback
    ADD CONSTRAINT fk_voice_feedback_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: voice_feedback fk_voice_feedback_tenant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_feedback
    ADD CONSTRAINT fk_voice_feedback_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: voice_feedback fk_voice_feedback_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_feedback
    ADD CONSTRAINT fk_voice_feedback_user FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: voice_feedback fk_voice_feedback_voice_log; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_feedback
    ADD CONSTRAINT fk_voice_feedback_voice_log FOREIGN KEY (voice_command_log_id) REFERENCES public.voice_command_log(id) ON DELETE SET NULL;


--
-- Name: webhook_delivery_attempt fk_webhook_delivery_attempt_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_delivery_attempt
    ADD CONSTRAINT fk_webhook_delivery_attempt_tenant_id FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: webhook_event_type fk_webhook_event_type_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event_type
    ADD CONSTRAINT fk_webhook_event_type_created_by FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: webhook_event_type fk_webhook_event_type_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event_type
    ADD CONSTRAINT fk_webhook_event_type_updated_by FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: idempotency_key idempotency_key_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_key
    ADD CONSTRAINT idempotency_key_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: idempotency_key idempotency_key_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_key
    ADD CONSTRAINT idempotency_key_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: in_app_notification in_app_notification_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.in_app_notification
    ADD CONSTRAINT in_app_notification_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: integration_credential integration_credential_app_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credential
    ADD CONSTRAINT integration_credential_app_service_id_fkey FOREIGN KEY (app_service_id) REFERENCES public.app_service(id);


--
-- Name: integration_credential integration_credential_initiated_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credential
    ADD CONSTRAINT integration_credential_initiated_by_user_id_fkey FOREIGN KEY (initiated_by_user_id) REFERENCES public."user"(id);


--
-- Name: integration_credential integration_credential_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credential
    ADD CONSTRAINT integration_credential_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: integration_sync_conflict integration_sync_conflict_app_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT integration_sync_conflict_app_service_id_fkey FOREIGN KEY (app_service_id) REFERENCES public.app_service(id);


--
-- Name: integration_sync_conflict integration_sync_conflict_entity_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT integration_sync_conflict_entity_type_code_fkey FOREIGN KEY (entity_type_code) REFERENCES public.entity_type(code);


--
-- Name: integration_sync_conflict integration_sync_conflict_pilot_modified_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT integration_sync_conflict_pilot_modified_by_user_id_fkey FOREIGN KEY (pilot_modified_by_user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: integration_sync_conflict integration_sync_conflict_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT integration_sync_conflict_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES public."user"(id);


--
-- Name: integration_sync_conflict integration_sync_conflict_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_conflict
    ADD CONSTRAINT integration_sync_conflict_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: integration_sync_log integration_sync_log_app_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_log
    ADD CONSTRAINT integration_sync_log_app_service_id_fkey FOREIGN KEY (app_service_id) REFERENCES public.app_service(id);


--
-- Name: integration_sync_log integration_sync_log_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_log
    ADD CONSTRAINT integration_sync_log_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id);


--
-- Name: integration_sync_log integration_sync_log_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_log
    ADD CONSTRAINT integration_sync_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: integration_sync_mapping integration_sync_mapping_app_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT integration_sync_mapping_app_service_id_fkey FOREIGN KEY (app_service_id) REFERENCES public.app_service(id);


--
-- Name: integration_sync_mapping integration_sync_mapping_entity_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT integration_sync_mapping_entity_type_code_fkey FOREIGN KEY (entity_type_code) REFERENCES public.entity_type(code);


--
-- Name: integration_sync_mapping integration_sync_mapping_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_sync_mapping
    ADD CONSTRAINT integration_sync_mapping_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: invoice invoice_currency_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_currency_fkey FOREIGN KEY (currency) REFERENCES public.currency(code);


--
-- Name: invoice invoice_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: invoice invoice_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: invoice_line invoice_line_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT invoice_line_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoice(id) ON DELETE RESTRICT;


--
-- Name: invoice_line invoice_line_pricebook_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT invoice_line_pricebook_item_id_fkey FOREIGN KEY (pricebook_item_id) REFERENCES public.pricebook_item(id);


--
-- Name: invoice_line invoice_line_qco_line_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT invoice_line_qco_line_type_id_fkey FOREIGN KEY (qco_line_type_id) REFERENCES public.qco_line_type(id);


--
-- Name: invoice_line_tax_component invoice_line_tax_component_invoice_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_tax_component
    ADD CONSTRAINT invoice_line_tax_component_invoice_line_id_fkey FOREIGN KEY (invoice_line_id) REFERENCES public.invoice_line(id) ON DELETE RESTRICT;


--
-- Name: invoice_line_tax_component invoice_line_tax_component_tax_rate_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_tax_component
    ADD CONSTRAINT invoice_line_tax_component_tax_rate_version_id_fkey FOREIGN KEY (tax_rate_version_id) REFERENCES public.tax_rate_version(id);


--
-- Name: invoice_line invoice_line_taxability_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line
    ADD CONSTRAINT invoice_line_taxability_code_fkey FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code);


--
-- Name: invoice invoice_payment_schedule_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_payment_schedule_line_id_fkey FOREIGN KEY (payment_schedule_line_id) REFERENCES public.payment_schedule_line(id) ON DELETE SET NULL;


--
-- Name: invoice invoice_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: invoice_signoff invoice_signoff_captured_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_signoff
    ADD CONSTRAINT invoice_signoff_captured_by_user_id_fkey FOREIGN KEY (captured_by_user_id) REFERENCES public."user"(id);


--
-- Name: invoice_signoff invoice_signoff_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_signoff
    ADD CONSTRAINT invoice_signoff_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoice(id);


--
-- Name: invoice_signoff invoice_signoff_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_signoff
    ADD CONSTRAINT invoice_signoff_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: invoice invoice_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.site(id) ON DELETE RESTRICT;


--
-- Name: invoice invoice_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.invoice_status(id);


--
-- Name: invoice_status invoice_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_status
    ADD CONSTRAINT invoice_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: invoice invoice_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job_attachment job_attachment_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_attachment
    ADD CONSTRAINT job_attachment_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: job_attachment job_attachment_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_attachment
    ADD CONSTRAINT job_attachment_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job job_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: job_expense_category job_expense_category_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense_category
    ADD CONSTRAINT job_expense_category_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: job_expense job_expense_invoice_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT job_expense_invoice_line_id_fkey FOREIGN KEY (invoice_line_id) REFERENCES public.invoice_line(id);


--
-- Name: job_expense job_expense_job_expense_category_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT job_expense_job_expense_category_code_fkey FOREIGN KEY (job_expense_category_code) REFERENCES public.job_expense_category(code);


--
-- Name: job_expense job_expense_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT job_expense_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: job_expense job_expense_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_expense
    ADD CONSTRAINT job_expense_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job job_job_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_job_type_id_fkey FOREIGN KEY (job_type_id) REFERENCES public.job_type(id) ON DELETE SET NULL;


--
-- Name: job_notes job_notes_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_notes
    ADD CONSTRAINT job_notes_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: job job_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: job job_quote_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_quote_version_id_fkey FOREIGN KEY (quote_version_id) REFERENCES public.quote_version(id) ON DELETE RESTRICT;


--
-- Name: job_recurrence_rule job_recurrence_rule_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_recurrence_rule
    ADD CONSTRAINT job_recurrence_rule_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: job_recurrence_rule job_recurrence_rule_default_tech_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_recurrence_rule
    ADD CONSTRAINT job_recurrence_rule_default_tech_user_id_fkey FOREIGN KEY (default_tech_user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: job job_recurrence_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_recurrence_rule_id_fkey FOREIGN KEY (recurrence_rule_id) REFERENCES public.job_recurrence_rule(id) ON DELETE SET NULL;


--
-- Name: job_recurrence_rule job_recurrence_rule_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_recurrence_rule
    ADD CONSTRAINT job_recurrence_rule_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.site(id) ON DELETE RESTRICT;


--
-- Name: job_recurrence_rule job_recurrence_rule_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_recurrence_rule
    ADD CONSTRAINT job_recurrence_rule_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job job_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.site(id) ON DELETE RESTRICT;


--
-- Name: job job_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.job_status(id);


--
-- Name: job_status job_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_status
    ADD CONSTRAINT job_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: job job_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job_time_entry job_time_entry_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT job_time_entry_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE RESTRICT;


--
-- Name: job_time_entry job_time_entry_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_time_entry
    ADD CONSTRAINT job_time_entry_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: job_type job_type_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_type
    ADD CONSTRAINT job_type_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: job_type job_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_type
    ADD CONSTRAINT job_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: job_type job_type_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_type
    ADD CONSTRAINT job_type_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: loto_confirmation loto_confirmation_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loto_confirmation
    ADD CONSTRAINT loto_confirmation_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: loto_confirmation loto_confirmation_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loto_confirmation
    ADD CONSTRAINT loto_confirmation_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE CASCADE;


--
-- Name: loto_confirmation loto_confirmation_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loto_confirmation
    ADD CONSTRAINT loto_confirmation_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: loto_confirmation loto_confirmation_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loto_confirmation
    ADD CONSTRAINT loto_confirmation_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mfa_grace_period_tracking mfa_grace_period_tracking_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mfa_grace_period_tracking
    ADD CONSTRAINT mfa_grace_period_tracking_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: mfa_grace_period_tracking mfa_grace_period_tracking_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mfa_grace_period_tracking
    ADD CONSTRAINT mfa_grace_period_tracking_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: mobile_device_push_token mobile_device_push_token_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT mobile_device_push_token_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: mobile_device_push_token mobile_device_push_token_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT mobile_device_push_token_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: mobile_device_push_token mobile_device_push_token_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT mobile_device_push_token_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: mobile_device_push_token mobile_device_push_token_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_device_push_token
    ADD CONSTRAINT mobile_device_push_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: mobile_push_permission_state mobile_push_permission_state_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_permission_state
    ADD CONSTRAINT mobile_push_permission_state_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_push_permission_state mobile_push_permission_state_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_permission_state
    ADD CONSTRAINT mobile_push_permission_state_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.mobile_device_push_token(device_id) ON DELETE RESTRICT;


--
-- Name: mobile_push_permission_state mobile_push_permission_state_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_permission_state
    ADD CONSTRAINT mobile_push_permission_state_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: mobile_push_permission_state mobile_push_permission_state_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_permission_state
    ADD CONSTRAINT mobile_push_permission_state_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_push_permission_state mobile_push_permission_state_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_permission_state
    ADD CONSTRAINT mobile_push_permission_state_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_push_rate_limit mobile_push_rate_limit_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_push_rate_limit
    ADD CONSTRAINT mobile_push_rate_limit_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: mobile_sync_event_audit mobile_sync_event_audit_escalation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event_audit
    ADD CONSTRAINT mobile_sync_event_audit_escalation_id_fkey FOREIGN KEY (escalation_id) REFERENCES public.mobile_sync_owner_escalation(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_event_audit mobile_sync_event_audit_originator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event_audit
    ADD CONSTRAINT mobile_sync_event_audit_originator_user_id_fkey FOREIGN KEY (originator_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_event_audit mobile_sync_event_audit_resolver_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event_audit
    ADD CONSTRAINT mobile_sync_event_audit_resolver_user_id_fkey FOREIGN KEY (resolver_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: mobile_sync_event_audit mobile_sync_event_audit_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_event_audit
    ADD CONSTRAINT mobile_sync_event_audit_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: mobile_sync_session mobile_sync_session_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_session
    ADD CONSTRAINT mobile_sync_session_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: mobile_sync_session mobile_sync_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mobile_sync_session
    ADD CONSTRAINT mobile_sync_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: nec_calculation_log nec_calculation_log_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: nec_calculation_log nec_calculation_log_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE SET NULL;


--
-- Name: nec_calculation_log nec_calculation_log_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: nec_calculation_log nec_calculation_log_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: nec_calculation_log nec_calculation_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nec_calculation_log
    ADD CONSTRAINT nec_calculation_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_category notification_category_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category
    ADD CONSTRAINT notification_category_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_category_sub_trigger notification_category_sub_trigger_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category_sub_trigger
    ADD CONSTRAINT notification_category_sub_trigger_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_category_sub_trigger notification_category_sub_trigger_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category_sub_trigger
    ADD CONSTRAINT notification_category_sub_trigger_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_category notification_category_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_category
    ADD CONSTRAINT notification_category_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_default_policy notification_default_policy_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_default_policy
    ADD CONSTRAINT notification_default_policy_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_default_policy notification_default_policy_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_default_policy
    ADD CONSTRAINT notification_default_policy_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: notification_default_policy notification_default_policy_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_default_policy
    ADD CONSTRAINT notification_default_policy_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_delivery_attempt notification_delivery_attempt_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_delivery_attempt
    ADD CONSTRAINT notification_delivery_attempt_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id);


--
-- Name: notification_delivery_attempt notification_delivery_attempt_notification_outbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_delivery_attempt
    ADD CONSTRAINT notification_delivery_attempt_notification_outbox_id_fkey FOREIGN KEY (notification_outbox_id) REFERENCES public.notification_outbox(id);


--
-- Name: notification_delivery_attempt notification_delivery_attempt_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_delivery_attempt
    ADD CONSTRAINT notification_delivery_attempt_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: notification_event notification_event_entity_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_event
    ADD CONSTRAINT notification_event_entity_type_code_fkey FOREIGN KEY (entity_type_code) REFERENCES public.entity_type(code);


--
-- Name: notification_event notification_event_notification_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_event
    ADD CONSTRAINT notification_event_notification_type_code_fkey FOREIGN KEY (notification_type_code) REFERENCES public.notification_type(code);


--
-- Name: notification_event notification_event_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_event
    ADD CONSTRAINT notification_event_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: notification_outbox notification_outbox_contact_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_contact_endpoint_id_fkey FOREIGN KEY (contact_endpoint_id) REFERENCES public.contact_endpoint(id);


--
-- Name: notification_outbox notification_outbox_notification_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_notification_event_id_fkey FOREIGN KEY (notification_event_id) REFERENCES public.notification_event(id);


--
-- Name: notification_outbox notification_outbox_recipient_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_recipient_contact_id_fkey FOREIGN KEY (recipient_contact_id) REFERENCES public.contact(id);


--
-- Name: notification_outbox notification_outbox_recipient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_recipient_user_id_fkey FOREIGN KEY (recipient_user_id) REFERENCES public."user"(id);


--
-- Name: notification_outbox notification_outbox_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: notification_outbox notification_outbox_user_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_user_endpoint_id_fkey FOREIGN KEY (user_endpoint_id) REFERENCES public.user_endpoint(id);


--
-- Name: notification_preference notification_preference_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preference
    ADD CONSTRAINT notification_preference_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_preference notification_preference_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preference
    ADD CONSTRAINT notification_preference_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: notification_template notification_template_notification_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_template
    ADD CONSTRAINT notification_template_notification_type_code_fkey FOREIGN KEY (notification_type_code) REFERENCES public.notification_type(code);


--
-- Name: notification_template notification_template_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_template
    ADD CONSTRAINT notification_template_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: notification_type notification_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_type
    ADD CONSTRAINT notification_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: password_policy password_policy_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_policy
    ADD CONSTRAINT password_policy_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: payment payment_connector_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_connector_config_id_fkey FOREIGN KEY (connector_config_id) REFERENCES public.connector_config(id);


--
-- Name: payment payment_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoice(id) ON DELETE RESTRICT;


--
-- Name: payment_method payment_method_billing_address_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT payment_method_billing_address_id_fkey FOREIGN KEY (billing_address_id) REFERENCES public.address(id);


--
-- Name: payment_method payment_method_payment_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT payment_method_payment_type_id_fkey FOREIGN KEY (payment_type_id) REFERENCES public.payment_type(id);


--
-- Name: payment_method payment_method_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_method
    ADD CONSTRAINT payment_method_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: payment payment_payment_method_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_payment_method_id_fkey FOREIGN KEY (payment_method_id) REFERENCES public.payment_method(id);


--
-- Name: payment_schedule payment_schedule_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule payment_schedule_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule payment_schedule_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.job(id) ON DELETE SET NULL;


--
-- Name: payment_schedule_line payment_schedule_line_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule_line
    ADD CONSTRAINT payment_schedule_line_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule_line payment_schedule_line_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule_line
    ADD CONSTRAINT payment_schedule_line_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoice(id) ON DELETE SET NULL;


--
-- Name: payment_schedule_line payment_schedule_line_payment_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule_line
    ADD CONSTRAINT payment_schedule_line_payment_schedule_id_fkey FOREIGN KEY (payment_schedule_id) REFERENCES public.payment_schedule(id) ON DELETE CASCADE;


--
-- Name: payment_schedule_line payment_schedule_line_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule_line
    ADD CONSTRAINT payment_schedule_line_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule_line payment_schedule_line_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule_line
    ADD CONSTRAINT payment_schedule_line_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule payment_schedule_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE SET NULL;


--
-- Name: payment_schedule payment_schedule_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.site(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule payment_schedule_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: payment_schedule payment_schedule_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_schedule
    ADD CONSTRAINT payment_schedule_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: payment payment_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.payment_status(id);


--
-- Name: payment_status payment_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_status
    ADD CONSTRAINT payment_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: payment payment_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: payment_type payment_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_type
    ADD CONSTRAINT payment_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: payment payment_variance_resolved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_variance_resolved_by_user_id_fkey FOREIGN KEY (variance_resolved_by_user_id) REFERENCES public."user"(id);


--
-- Name: platform_setting_catalog platform_setting_catalog_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting_catalog
    ADD CONSTRAINT platform_setting_catalog_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: platform_setting_catalog platform_setting_catalog_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting_catalog
    ADD CONSTRAINT platform_setting_catalog_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: platform_setting platform_setting_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting
    ADD CONSTRAINT platform_setting_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: platform_setting platform_setting_key_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting
    ADD CONSTRAINT platform_setting_key_fkey FOREIGN KEY (key) REFERENCES public.platform_setting_catalog(key) ON DELETE RESTRICT;


--
-- Name: platform_setting platform_setting_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting
    ADD CONSTRAINT platform_setting_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;


--
-- Name: platform_setting platform_setting_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_setting
    ADD CONSTRAINT platform_setting_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: pricebook_item pricebook_item_taxability_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT pricebook_item_taxability_code_fkey FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code);


--
-- Name: pricebook_item pricebook_item_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT pricebook_item_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: pricebook_item pricebook_item_uom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item
    ADD CONSTRAINT pricebook_item_uom_id_fkey FOREIGN KEY (uom_id) REFERENCES public.supplier_item_uom(id);


--
-- Name: pricebook_item_version pricebook_item_version_pricebook_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item_version
    ADD CONSTRAINT pricebook_item_version_pricebook_item_id_fkey FOREIGN KEY (pricebook_item_id) REFERENCES public.pricebook_item(id);


--
-- Name: pricebook_item_version pricebook_item_version_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricebook_item_version
    ADD CONSTRAINT pricebook_item_version_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: pricing_cache pricing_cache_currency_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache
    ADD CONSTRAINT pricing_cache_currency_fkey FOREIGN KEY (currency) REFERENCES public.currency(code);


--
-- Name: pricing_cache pricing_cache_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache
    ADD CONSTRAINT pricing_cache_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(id);


--
-- Name: pricing_cache pricing_cache_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_cache
    ADD CONSTRAINT pricing_cache_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: product_plan_product_feature_version product_plan_product_feature_version_product_feature_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_product_feature_version
    ADD CONSTRAINT product_plan_product_feature_version_product_feature_code_fkey FOREIGN KEY (product_feature_code) REFERENCES public.product_feature(code);


--
-- Name: product_plan_product_feature_version product_plan_product_feature_version_product_plan_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_product_feature_version
    ADD CONSTRAINT product_plan_product_feature_version_product_plan_code_fkey FOREIGN KEY (product_plan_code) REFERENCES public.product_plan(code);


--
-- Name: product_plan_version product_plan_version_product_plan_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_plan_version
    ADD CONSTRAINT product_plan_version_product_plan_code_fkey FOREIGN KEY (product_plan_code) REFERENCES public.product_plan(code);


--
-- Name: psp_customer psp_customer_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_customer
    ADD CONSTRAINT psp_customer_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: psp_customer psp_customer_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_customer
    ADD CONSTRAINT psp_customer_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: psp_transaction_log psp_transaction_log_app_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_transaction_log
    ADD CONSTRAINT psp_transaction_log_app_service_id_fkey FOREIGN KEY (app_service_id) REFERENCES public.app_service(id);


--
-- Name: psp_transaction_log psp_transaction_log_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_transaction_log
    ADD CONSTRAINT psp_transaction_log_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payment(id) ON DELETE RESTRICT;


--
-- Name: psp_transaction_log psp_transaction_log_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psp_transaction_log
    ADD CONSTRAINT psp_transaction_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: qco_line_type qco_line_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qco_line_type
    ADD CONSTRAINT qco_line_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: qpl_contact_action_type qpl_contact_action_type_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qpl_contact_action_type
    ADD CONSTRAINT qpl_contact_action_type_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: quote_acceptance quote_acceptance_accepted_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT quote_acceptance_accepted_by_user_id_fkey FOREIGN KEY (accepted_by_user_id) REFERENCES public."user"(id);


--
-- Name: quote_acceptance quote_acceptance_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT quote_acceptance_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: quote_acceptance quote_acceptance_quote_public_link_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT quote_acceptance_quote_public_link_id_fkey FOREIGN KEY (quote_public_link_id) REFERENCES public.quote_public_link(id);


--
-- Name: quote_acceptance quote_acceptance_quote_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_acceptance
    ADD CONSTRAINT quote_acceptance_quote_version_id_fkey FOREIGN KEY (quote_version_id) REFERENCES public.quote_version(id) ON DELETE RESTRICT;


--
-- Name: quote quote_currency_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT quote_currency_fkey FOREIGN KEY (currency) REFERENCES public.currency(code);


--
-- Name: quote quote_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT quote_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: quote_line quote_line_pricebook_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_pricebook_item_id_fkey FOREIGN KEY (pricebook_item_id) REFERENCES public.pricebook_item(id);


--
-- Name: quote_line quote_line_qco_line_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_qco_line_type_id_fkey FOREIGN KEY (qco_line_type_id) REFERENCES public.qco_line_type(id);


--
-- Name: quote_line quote_line_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: quote_line quote_line_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(id);


--
-- Name: quote_line quote_line_supplier_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_supplier_item_id_fkey FOREIGN KEY (supplier_item_id) REFERENCES public.supplier_item(id);


--
-- Name: quote_line_tax_component quote_line_tax_component_quote_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line_tax_component
    ADD CONSTRAINT quote_line_tax_component_quote_line_id_fkey FOREIGN KEY (quote_line_id) REFERENCES public.quote_line(id) ON DELETE RESTRICT;


--
-- Name: quote_line_tax_component quote_line_tax_component_tax_rate_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line_tax_component
    ADD CONSTRAINT quote_line_tax_component_tax_rate_version_id_fkey FOREIGN KEY (tax_rate_version_id) REFERENCES public.tax_rate_version(id);


--
-- Name: quote_line quote_line_taxability_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_line
    ADD CONSTRAINT quote_line_taxability_code_fkey FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code);


--
-- Name: quote_link_status quote_link_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_link_status
    ADD CONSTRAINT quote_link_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: quote_message quote_message_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_message
    ADD CONSTRAINT quote_message_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: quote_message quote_message_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_message
    ADD CONSTRAINT quote_message_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: quote_message quote_message_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_message
    ADD CONSTRAINT quote_message_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link_contact_action quote_public_link_contact_actio_qpl_contact_action_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT quote_public_link_contact_actio_qpl_contact_action_type_id_fkey FOREIGN KEY (qpl_contact_action_type_id) REFERENCES public.qpl_contact_action_type(id);


--
-- Name: quote_public_link_contact_action quote_public_link_contact_action_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT quote_public_link_contact_action_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: quote_public_link_contact_action quote_public_link_contact_action_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT quote_public_link_contact_action_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link_contact_action quote_public_link_contact_action_quote_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link_contact_action
    ADD CONSTRAINT quote_public_link_contact_action_quote_version_id_fkey FOREIGN KEY (quote_version_id) REFERENCES public.quote_version(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link quote_public_link_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT quote_public_link_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contact(id);


--
-- Name: quote_public_link quote_public_link_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT quote_public_link_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: quote_public_link quote_public_link_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_public_link
    ADD CONSTRAINT quote_public_link_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.quote_link_status(id);


--
-- Name: quote quote_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT quote_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.site(id) ON DELETE RESTRICT;


--
-- Name: quote quote_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT quote_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.quote_status(id);


--
-- Name: quote_status quote_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_status
    ADD CONSTRAINT quote_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote quote_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote
    ADD CONSTRAINT quote_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: quote_version quote_version_quote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quote_version
    ADD CONSTRAINT quote_version_quote_id_fkey FOREIGN KEY (quote_id) REFERENCES public.quote(id) ON DELETE RESTRICT;


--
-- Name: site site_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site
    ADD CONSTRAINT site_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


--
-- Name: site site_lifecycle_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site
    ADD CONSTRAINT site_lifecycle_status_id_fkey FOREIGN KEY (lifecycle_status_id) REFERENCES public.site_lifecycle_status(id);


--
-- Name: site_lifecycle_status site_lifecycle_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_lifecycle_status
    ADD CONSTRAINT site_lifecycle_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: site site_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site
    ADD CONSTRAINT site_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: sms_quota_period sms_quota_period_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sms_quota_period
    ADD CONSTRAINT sms_quota_period_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: stripe_webhook_event_processed stripe_webhook_event_processed_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stripe_webhook_event_processed
    ADD CONSTRAINT stripe_webhook_event_processed_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription subscription_product_plan_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_product_plan_code_fkey FOREIGN KEY (product_plan_code) REFERENCES public.product_plan(code);


--
-- Name: subscription subscription_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.subscription_status(id);


--
-- Name: subscription_status subscription_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_status
    ADD CONSTRAINT subscription_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: subscription subscription_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: subscription_tier subscription_tier_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_tier
    ADD CONSTRAINT subscription_tier_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription_tier subscription_tier_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_tier
    ADD CONSTRAINT subscription_tier_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: subscription_usage subscription_usage_product_feature_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT subscription_usage_product_feature_code_fkey FOREIGN KEY (product_feature_code) REFERENCES public.product_feature(code);


--
-- Name: subscription_usage subscription_usage_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_usage
    ADD CONSTRAINT subscription_usage_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscription(id);


--
-- Name: supplier_item supplier_item_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT supplier_item_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.supplier_item_category(id);


--
-- Name: supplier_item_category supplier_item_category_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_category
    ADD CONSTRAINT supplier_item_category_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: supplier_item_price supplier_item_price_currency_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price
    ADD CONSTRAINT supplier_item_price_currency_fkey FOREIGN KEY (currency) REFERENCES public.currency(code);


--
-- Name: supplier_item_price supplier_item_price_supplier_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price
    ADD CONSTRAINT supplier_item_price_supplier_item_id_fkey FOREIGN KEY (supplier_item_id) REFERENCES public.supplier_item(id);


--
-- Name: supplier_item_price supplier_item_price_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_price
    ADD CONSTRAINT supplier_item_price_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: supplier_item supplier_item_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT supplier_item_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(id);


--
-- Name: supplier_item supplier_item_taxability_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT supplier_item_taxability_code_fkey FOREIGN KEY (taxability_code) REFERENCES public.taxability_code(code);


--
-- Name: supplier_item supplier_item_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT supplier_item_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: supplier_item supplier_item_uom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item
    ADD CONSTRAINT supplier_item_uom_id_fkey FOREIGN KEY (uom_id) REFERENCES public.supplier_item_uom(id);


--
-- Name: supplier_item_uom supplier_item_uom_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_item_uom
    ADD CONSTRAINT supplier_item_uom_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: supplier supplier_lifecycle_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier
    ADD CONSTRAINT supplier_lifecycle_status_id_fkey FOREIGN KEY (lifecycle_status_id) REFERENCES public.supplier_lifecycle_status(id);


--
-- Name: supplier_lifecycle_status supplier_lifecycle_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_lifecycle_status
    ADD CONSTRAINT supplier_lifecycle_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: supplier supplier_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier
    ADD CONSTRAINT supplier_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_10dlc_profile tenant_10dlc_profile_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_10dlc_profile
    ADD CONSTRAINT tenant_10dlc_profile_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_10dlc_profile tenant_10dlc_profile_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_10dlc_profile
    ADD CONSTRAINT tenant_10dlc_profile_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_10dlc_profile tenant_10dlc_profile_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_10dlc_profile
    ADD CONSTRAINT tenant_10dlc_profile_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_domain tenant_domain_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_domain
    ADD CONSTRAINT tenant_domain_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_legal_acceptance tenant_legal_acceptance_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_legal_acceptance
    ADD CONSTRAINT tenant_legal_acceptance_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_legal_acceptance tenant_legal_acceptance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_legal_acceptance
    ADD CONSTRAINT tenant_legal_acceptance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_markup_version tenant_markup_version_job_expense_category_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_markup_version
    ADD CONSTRAINT tenant_markup_version_job_expense_category_code_fkey FOREIGN KEY (job_expense_category_code) REFERENCES public.job_expense_category(code);


--
-- Name: tenant_markup_version tenant_markup_version_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_markup_version
    ADD CONSTRAINT tenant_markup_version_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_messaging_registration tenant_messaging_registration_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_messaging_registration
    ADD CONSTRAINT tenant_messaging_registration_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_onboarding_checklist tenant_onboarding_checklist_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_onboarding_checklist
    ADD CONSTRAINT tenant_onboarding_checklist_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_onboarding_checklist tenant_onboarding_checklist_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_onboarding_checklist
    ADD CONSTRAINT tenant_onboarding_checklist_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_phone_number tenant_phone_number_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_phone_number
    ADD CONSTRAINT tenant_phone_number_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_phone_number tenant_phone_number_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_phone_number
    ADD CONSTRAINT tenant_phone_number_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: tenant_phone_number tenant_phone_number_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_phone_number
    ADD CONSTRAINT tenant_phone_number_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_product_feature_override tenant_product_feature_override_product_feature_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_product_feature_override
    ADD CONSTRAINT tenant_product_feature_override_product_feature_code_fkey FOREIGN KEY (product_feature_code) REFERENCES public.product_feature(code);


--
-- Name: tenant_product_feature_override tenant_product_feature_override_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_product_feature_override
    ADD CONSTRAINT tenant_product_feature_override_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_signup tenant_signup_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_signup
    ADD CONSTRAINT tenant_signup_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_signup tenant_signup_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_signup
    ADD CONSTRAINT tenant_signup_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_site tenant_site_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_site
    ADD CONSTRAINT tenant_site_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_subscription_usage tenant_subscription_usage_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_subscription_usage
    ADD CONSTRAINT tenant_subscription_usage_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_subscription_usage tenant_subscription_usage_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_subscription_usage
    ADD CONSTRAINT tenant_subscription_usage_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_tier_override tenant_tier_override_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_tier_override
    ADD CONSTRAINT tenant_tier_override_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_tier_override tenant_tier_override_override_tier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_tier_override
    ADD CONSTRAINT tenant_tier_override_override_tier_id_fkey FOREIGN KEY (override_tier_id) REFERENCES public.subscription_tier(tier_id) ON DELETE RESTRICT;


--
-- Name: tenant_tier_override tenant_tier_override_set_by_operator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_tier_override
    ADD CONSTRAINT tenant_tier_override_set_by_operator_user_id_fkey FOREIGN KEY (set_by_operator_user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_tier_override tenant_tier_override_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_tier_override
    ADD CONSTRAINT tenant_tier_override_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: tenant_user_invite tenant_user_invite_invited_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_invite
    ADD CONSTRAINT tenant_user_invite_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES public."user"(id);


--
-- Name: tenant_user_invite tenant_user_invite_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_invite
    ADD CONSTRAINT tenant_user_invite_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_user tenant_user_role_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_role_code_fkey FOREIGN KEY (role_code) REFERENCES public.tenant_user_role(code);


--
-- Name: tenant_user tenant_user_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.tenant_user_status(id);


--
-- Name: tenant_user_status tenant_user_status_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user_status
    ADD CONSTRAINT tenant_user_status_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_user tenant_user_suspended_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_suspended_by_fkey FOREIGN KEY (suspended_by) REFERENCES public."user"(id);


--
-- Name: tenant_user tenant_user_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: tenant_user tenant_user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_user
    ADD CONSTRAINT tenant_user_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: usage_ledger usage_ledger_product_feature_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_product_feature_code_fkey FOREIGN KEY (product_feature_code) REFERENCES public.product_feature(code);


--
-- Name: usage_ledger usage_ledger_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscription(id) ON DELETE RESTRICT;


--
-- Name: usage_ledger usage_ledger_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_ledger
    ADD CONSTRAINT usage_ledger_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: user_endpoint user_endpoint_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_endpoint
    ADD CONSTRAINT user_endpoint_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user_mfa_method user_mfa_method_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_method
    ADD CONSTRAINT user_mfa_method_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_mfa_method user_mfa_method_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_method
    ADD CONSTRAINT user_mfa_method_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user_mfa_recovery_code user_mfa_recovery_code_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_recovery_code
    ADD CONSTRAINT user_mfa_recovery_code_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_mfa_recovery_code user_mfa_recovery_code_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_mfa_recovery_code
    ADD CONSTRAINT user_mfa_recovery_code_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user user_platform_role_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_platform_role_code_fkey FOREIGN KEY (platform_role_code) REFERENCES public.platform_role(code);


--
-- Name: user_preference user_preference_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_preference
    ADD CONSTRAINT user_preference_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_preference user_preference_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_preference
    ADD CONSTRAINT user_preference_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user_session_history user_session_history_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session_history
    ADD CONSTRAINT user_session_history_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_session_history user_session_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session_history
    ADD CONSTRAINT user_session_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user_session_metadata user_session_metadata_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session_metadata
    ADD CONSTRAINT user_session_metadata_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_session_metadata user_session_metadata_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_session_metadata
    ADD CONSTRAINT user_session_metadata_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user_sms_consent_audit user_sms_consent_audit_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sms_consent_audit
    ADD CONSTRAINT user_sms_consent_audit_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_sms_consent_audit user_sms_consent_audit_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sms_consent_audit
    ADD CONSTRAINT user_sms_consent_audit_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: user_sms_consent_audit user_sms_consent_audit_user_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sms_consent_audit
    ADD CONSTRAINT user_sms_consent_audit_user_endpoint_id_fkey FOREIGN KEY (user_endpoint_id) REFERENCES public.user_endpoint(id) ON DELETE RESTRICT;


--
-- Name: user_sms_consent_audit user_sms_consent_audit_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sms_consent_audit
    ADD CONSTRAINT user_sms_consent_audit_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE RESTRICT;


--
-- Name: user_sso_identity user_sso_identity_sso_provider_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sso_identity
    ADD CONSTRAINT user_sso_identity_sso_provider_code_fkey FOREIGN KEY (sso_provider_code) REFERENCES public.sso_provider(code);


--
-- Name: user_sso_identity user_sso_identity_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sso_identity
    ADD CONSTRAINT user_sso_identity_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: voice_command_entity_link voice_command_entity_link_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_entity_link
    ADD CONSTRAINT voice_command_entity_link_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE RESTRICT;


--
-- Name: voice_command_entity_link voice_command_entity_link_voice_command_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_entity_link
    ADD CONSTRAINT voice_command_entity_link_voice_command_log_id_fkey FOREIGN KEY (voice_command_log_id) REFERENCES public.voice_command_log(id) ON DELETE RESTRICT;


--
-- Name: voice_command_log voice_command_log_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_log
    ADD CONSTRAINT voice_command_log_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.conversation_message(id);


--
-- Name: voice_command_log voice_command_log_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_log
    ADD CONSTRAINT voice_command_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: voice_command_log voice_command_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_command_log
    ADD CONSTRAINT voice_command_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: webhook_delivery_attempt webhook_delivery_attempt_webhook_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_delivery_attempt
    ADD CONSTRAINT webhook_delivery_attempt_webhook_endpoint_id_fkey FOREIGN KEY (webhook_endpoint_id) REFERENCES public.webhook_endpoint(id);


--
-- Name: webhook_delivery_attempt webhook_delivery_attempt_webhook_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_delivery_attempt
    ADD CONSTRAINT webhook_delivery_attempt_webhook_event_id_fkey FOREIGN KEY (webhook_event_id) REFERENCES public.webhook_event(id);


--
-- Name: webhook_endpoint webhook_endpoint_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_endpoint
    ADD CONSTRAINT webhook_endpoint_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: webhook_event webhook_event_entity_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event
    ADD CONSTRAINT webhook_event_entity_type_code_fkey FOREIGN KEY (entity_type_code) REFERENCES public.entity_type(code);


--
-- Name: webhook_event webhook_event_event_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event
    ADD CONSTRAINT webhook_event_event_type_code_fkey FOREIGN KEY (event_type_code) REFERENCES public.webhook_event_type(code);


--
-- Name: webhook_event webhook_event_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event
    ADD CONSTRAINT webhook_event_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- PostgreSQL database dump complete
--

\unrestrict hC4c34mPb0LbSDb8V5xydOtfnk52BHSLfsIPoccNrrvvriaoX809hg167LAgRDx

