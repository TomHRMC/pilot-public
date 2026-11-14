import { healthHandlers } from "./health";
import { authHandlers } from "./auth";
import { voiceHttpHandlers } from "./voice";
// voiceWsHandler is intentionally NOT imported here — it lives in ./voice.ws
// (dev-runtime only). Importing it would evaluate ws.link() at module-load
// time and poison the Jest/jsdom environment (TEST-UPLIFT-1C §G Q1).
// mocks/browser.ts composes the WS handler itself for the dev runtime.
import { syncHandlers } from "./sync";
import { photoHandlers } from "./photos";
import { communicationsHandlers } from "./communicationsHandlers";
import { customerCommsPreviewHandlers } from "./customerCommsPreviewHandlers";
// MOB-B1: Jobs list handlers
import { jobsHandlers } from "./jobsHandlers";
// MOB-B2: Job detail handlers
import { jobDetailHandlers } from "./jobDetailHandlers";
// MOB-B3: Customers list + detail + sites
import { customersHandlers } from "./customersHandlers";
// MOB-B5: Owner dashboard sections
import { ownerHandlers } from "./ownerHandlers";
// MOB-B4: NEC calculator endpoints
import { necHandlers } from "./necHandlers";
// MOB-B7: LOTO policy + customer create
import { settingsHandlers } from "./settingsHandlers";
// MOB-B8: Background sync policy + push token registration
import { backgroundSyncHandlers } from "./backgroundSyncHandlers";
// MOB-B10: Account settings — profile + MFA status
import { accountSettingsHandlers } from "./accountSettingsHandlers";
// CE-1 Part B: Invoice sign-off context + capture
import { invoiceSignoffHandlers } from "./invoiceSignoffHandlers";

export const handlers = [
  ...healthHandlers,
  ...authHandlers,
  ...voiceHttpHandlers,
  ...syncHandlers,
  ...photoHandlers,
  // FE-B10: SMS threads / mobile inbox
  ...communicationsHandlers,
  // FE-B6: Customer comms preview/send templates
  ...customerCommsPreviewHandlers,
  // MOB-B1: Jobs list (assigned tech jobs)
  ...jobsHandlers,
  // MOB-B2: Job detail (clock in/out, expenses, notes, LOTO, change orders, margin)
  ...jobDetailHandlers,
  // MOB-B3: Customers list + detail + sites
  ...customersHandlers,
  // MOB-B5: Owner dashboard sections
  ...ownerHandlers,
  // MOB-B4: NEC calculator endpoints
  ...necHandlers,
  // MOB-B7: LOTO policy + customer create
  ...settingsHandlers,
  // MOB-B8: Background sync policy + push token registration
  ...backgroundSyncHandlers,
  // MOB-B10: Account settings — profile + MFA status
  ...accountSettingsHandlers,
  // CE-1 Part B: Invoice sign-off context + capture
  ...invoiceSignoffHandlers,
];
