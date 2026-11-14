-- Switching between Founders mode and Post-Beta Mode

-- Switch to Post-Beta Mode

-- 1. Activate Starter + Teams plans (marketing page switch)
UPDATE public.product_plan SET is_active = true, updated_at = NOW()
WHERE code IN ('starter_plan', 'teams');

-- 2. Deactivate Founders plan (closes new Founder signups)
UPDATE public.product_plan SET is_active = false, updated_at = NOW()
WHERE code = 'founders_plan';

-- 3. Activate Trial + Starter + Teams tiers (signup flow tier picker)
UPDATE public.subscription_tier SET is_active = true, updated_at = NOW()
WHERE tier_name IN ('trial', 'starter', 'teams');

-- 4. Deactivate Founders tier (prevents new users being routed to founders tier)
UPDATE public.subscription_tier SET is_active = false, updated_at = NOW()
WHERE tier_name = 'founders';

-- Switch to Founders Mode

-- 1. Activate Starter + Teams plans (marketing page switch)
UPDATE public.product_plan SET is_active = false, updated_at = NOW()
WHERE code IN ('starter_plan', 'teams');

-- 2. Deactivate Founders plan (closes new Founder signups)
UPDATE public.product_plan SET is_active = true, updated_at = NOW()
WHERE code = 'founders_plan';

-- 3. Activate Trial + Starter + Teams tiers (signup flow tier picker)
UPDATE public.subscription_tier SET is_active = false, updated_at = NOW()
WHERE tier_name IN ('trial', 'starter', 'teams');

-- 4. Deactivate Founders tier (prevents new users being routed to founders tier)
UPDATE public.subscription_tier SET is_active = true, updated_at = NOW()
WHERE tier_name = 'founders';

-- Insert now rows into product_plan and subscription_tier tables - Founders mode

-- ── product_plan ──────────────────────────────────────────────────────────
INSERT INTO public.product_plan
  (code, name, description, is_active, created_at, updated_at)
VALUES
  -- Only active plan during Founders cohort
  ('founders_plan', 'Founders Plan',
   'Time-limited founding member cohort plan. 6 months free, then $49/mo locked at Starter limits for life.',
   true,  NOW(), NOW()),

  -- Dormant until general release (flip is_active=true when ready)
  ('starter_plan', 'Starter Plan',
   'For solo contractors starting out. 5 schedule lanes, 90 Voice AI min/mo, 100 SMS segs/mo.',
   false, NOW(), NOW()),

  -- Dormant until general release (flip is_active=true when ready)
  ('teams', 'Teams Plan',
   'For growing contractors and small teams. 20 schedule lanes, 300 Voice AI min/mo, 500 SMS segs/mo.',
   false, NOW(), NOW())

ON CONFLICT (code) DO NOTHING;

-- ── subscription_tier ─────────────────────────────────────────────────────
INSERT INTO public.subscription_tier
  (tier_id, tier_name, display_label, monthly_price_cents, is_trial,
   trial_duration_days, is_active, display_order, schedule_lanes,
   stripe_price_id, product_plan_code)
VALUES
  -- Founders: only active tier during cohort period
  (gen_random_uuid(), 'founders', 'Founders', 0, false,
   NULL, true, 0, 5, NULL, 'founders_plan'),

  -- Trial: inactive until general release (turns on with starter/teams)
  (gen_random_uuid(), 'trial', 'Trial', 0, true,
   14, false, 1, 5, NULL, 'starter_plan'),

  -- Starter: $49/mo, inactive until general release
  (gen_random_uuid(), 'starter', 'Starter', 4900, false,
   NULL, false, 2, 5, NULL, 'starter_plan'),

  -- Teams: $149/mo, inactive until general release
  (gen_random_uuid(), 'teams', 'Teams', 14900, false,
   NULL, false, 3, 20, NULL, 'teams')

ON CONFLICT (tier_name) DO NOTHING;
