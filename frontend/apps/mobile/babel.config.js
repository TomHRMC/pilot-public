/**
 * Babel configuration — apps/mobile
 *
 * Location: apps/mobile/babel.config.js
 *
 * ── WatermelonDB decorator requirements ──────────────────────────────────────
 * WatermelonDB uses TypeScript legacy decorators (@field, @text, @date, etc.)
 * which require @babel/plugin-proposal-decorators with { legacy: true }.
 *
 * CRITICAL ORDER: decorators MUST come before class-properties.  In Babel's
 * plugin/preset pipeline, explicit `plugins` always run before `presets`, so
 * listing the decorator plugin here guarantees it runs before babel-preset-expo
 * handles class-properties internally.
 *
 * ── Class properties: assumptions, not an explicit plugin ────────────────────
 * We do NOT list @babel/plugin-transform-class-properties in plugins here.
 * babel-preset-expo already includes this plugin internally.  Adding it a
 * second time causes double-transformation of class fields, which corrupts
 * React Native's frozen static constants (e.g. Event.NONE, Event.BUBBLING_PHASE)
 * producing:
 *   "TypeError: Cannot assign to read-only property 'NONE'"
 *
 * Instead, we use the `assumptions` API (Babel 7.13+) to set the semantics
 * for class-properties WITHOUT re-running the transform:
 *   setPublicClassFields: true  — uses simple assignment (obj.prop = val)
 *     instead of Object.defineProperty.  Required for non-decorated class
 *     fields in React Native components.
 *   privateFieldsAsSymbols: true — required companion when legacy decorators
 *     and setPublicClassFields are combined; suppresses the
 *     "[transform-private-methods] loose mode conflict" warning from Metro.
 *
 * ── WatermelonDB model fields: use `declare` not `!` ────────────────────────
 * @babel/plugin-proposal-decorators@7.25+ (shipped in babel-preset-expo@54)
 * throws "Definitely assigned fields cannot be initialized here, but only in
 * the constructor" when it sees `@decorator() field!: Type` syntax.
 *
 * The fix: all WatermelonDB model properties use `declare` instead of `!`:
 *   ❌  @field("col") jobId!: string;
 *   ✅  @field("col") declare jobId: string;
 *
 * `declare` is TypeScript-only and emits no JavaScript — Babel never sees a
 * conflicting field initializer, so the legacy decorator transform succeeds.
 * This is the correct pattern per WatermelonDB docs for TypeScript 4.3+.
 */

module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      // Step 1: Strip TypeScript FIRST (with allowDeclareFields:true so that
      // `declare field: Type` on WatermelonDB model classes is recognized).
      //
      // `declare` is TypeScript-only syntax that emits no JS output — it signals
      // to TypeScript that a class member exists without emitting a class field
      // initializer.  @babel/plugin-proposal-decorators@7.25+ throws:
      //   "Definitely assigned fields cannot be initialized here, but only in
      //    the constructor"
      // when it sees decorated fields with the `!` suffix (definite assignment
      // assertion), because `!` causes Babel to emit a class field initializer
      // that conflicts with legacy decorator transforms.
      //
      // The fix: switch all WatermelonDB model fields to `declare field: Type`
      // (TypeScript 4.3+ pattern, supported by WatermelonDB).  Then ensure
      // `@babel/plugin-transform-typescript` runs FIRST (plugins run before
      // presets) and strips the `declare` keyword before the decorators plugin
      // ever sees the field — so it never encounters a conflicting initializer.
      //
      // allowDeclareFields:true enables stripping of `declare` class fields.
      // By the time babel-preset-expo's internal TS transform runs (later,
      // as a preset), there is nothing TypeScript left to process.
      [
        "@babel/plugin-transform-typescript",
        { allowDeclareFields: true, isTSX: true },
      ],

      // Step 2: Legacy decorators — runs AFTER TS is stripped (above), so
      // the decorated class fields are already plain JS property assignments
      // without any conflicting `!` or `declare` modifiers.
      // babel-preset-expo (a preset) runs AFTER all plugins, so this runs
      // before the preset's internal class-properties transform.
      ["@babel/plugin-proposal-decorators", { legacy: true }],
    ],
    assumptions: {
      setPublicClassFields: true,
      privateFieldsAsSymbols: true,
    },
  };
};
