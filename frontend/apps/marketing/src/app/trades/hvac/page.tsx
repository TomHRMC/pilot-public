// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import TradePageTemplate from "../../../components/trades/TradePageTemplate";
import type {
  PainPoint,
  Feature,
  VoiceCard,
  FAQ,
} from "../../../components/trades/TradePageTemplate";
import { getSiteMode } from "../../../lib/useSiteMode";

export const metadata: Metadata = {
  title: "HVAC Contractor Software — AI Voice Quoting & Business Management",
  description:
    "Built for HVAC techs. Voice-powered estimating with real-time equipment pricing, load calculation references, and seasonal dispatch tools. Start your free trial.",
  keywords: [
    "HVAC estimating software",
    "HVAC business management",
    "HVAC contractor software",
    "HVAC bidding software",
  ],
  openGraph: {
    title:
      "HVAC Contractor Software — AI Voice Quoting & Business Management | Pilot for Trades",
    description:
      "Built for HVAC techs. Voice-powered estimating with real-time equipment pricing, load calculation references, and seasonal dispatch tools.",
    url: "https://pilotfortrades.com/trades/hvac",
    images: [
      {
        url: "/og-trades-hvac.png",
        width: 1200,
        height: 630,
        alt: "Pilot for Trades — AI Voice Quoting for HVAC Contractors",
      },
    ],
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    {
      "@type": "ListItem",
      position: 1,
      name: "Home",
      item: "https://pilotfortrades.com",
    },
    {
      "@type": "ListItem",
      position: 2,
      name: "Trades",
      item: "https://pilotfortrades.com/trades/hvac",
    },
    {
      "@type": "ListItem",
      position: 3,
      name: "HVAC",
      item: "https://pilotfortrades.com/trades/hvac",
    },
  ],
};

const painPoints: PainPoint[] = [
  {
    iconName: "Thermometer",
    stat: "Equipment Costs",
    title: "Unit Prices Shift Without Warning",
    description:
      "Carrier, Trane, Lennox — manufacturer pricing updates land quarterly, sometimes mid-season. A system you quoted at $3,800 last month might cost you $4,200 today. That $400 gap comes straight from your profit.",
  },
  {
    iconName: "CalendarDays",
    stat: "Seasonal Surges",
    title: "June Hits and Everything Breaks",
    description:
      "First heat wave of the summer means 40 calls in two days. Dispatching techs across a service area while keeping customers updated and managing callbacks is a logistics nightmare — especially without a dispatcher.",
  },
  {
    iconName: "Calculator",
    stat: "Complex Bids",
    title: "Load Calcs and Equipment Bids Take Hours",
    description:
      "A residential system replacement means Manual J load calculations, equipment selection, ductwork assessment, refrigerant line sizing, and building a detailed bid — often late at night after a full day of service calls.",
  },
];

const features: Feature[] = [
  {
    iconName: "Mic",
    title: "Talk Through the Job. Get the Bid.",
    description:
      'Stand in the mechanical room and describe the scope: "3-ton Carrier 16 SEER2 split system, existing ductwork is good, need new line set, 40 feet, disconnect, and pad." Pilot builds the bid while you\'re still on-site.',
    linkLabel: "See Voice AI →",
    linkHref: "/features#voice-ai",
  },
  {
    iconName: "DollarSign",
    title: "Equipment Costs That Aren't Last Quarter's",
    description:
      "Pilot tracks equipment pricing for major manufacturers — condensers, air handlers, furnaces, mini-splits, and components. Your bids reflect today's costs, not a stale price sheet pinned to your office wall.",
    linkLabel: "See Pricing Engine →",
    linkHref: "/features#quoting",
  },
  {
    iconName: "Calendar",
    title: "Dispatch That Survives Peak Season",
    description:
      "First heat wave? First cold snap? Pilot's dispatch board handles the surge — route techs by proximity, manage appointment windows, auto-notify customers with ETAs, and keep callbacks organized. No more sticky notes on the dashboard.",
    linkLabel: "See Dispatch →",
    linkHref: "/features#dispatch",
  },
  {
    iconName: "BarChart3",
    title: "Margin Visibility on Every Install",
    description:
      "Track equipment cost, materials, labor hours, and refrigerant against the quoted price — as the job happens, not weeks later. Know immediately if that changeout made money or broke even.",
    linkLabel: "See Profitability →",
    linkHref: "/features#profitability",
  },
];

const voiceExamples: VoiceCard[] = [
  {
    command:
      "Quote a 3-ton Carrier 24ACC636 condenser with a matching FE4ANF003 air handler, new line set at 35 feet, disconnect, pad, and thermostat upgrade to an Ecobee.",
    response:
      "Equipment, line set, disconnect, pad, thermostat, refrigerant charge, labor, permit — full line-item bid with current pricing.",
  },
  {
    command:
      "Add a ductwork modification — extend supply run 15 feet to the master bedroom addition, 8-inch flex, one register, insulated.",
    response:
      "Materials, hangers, register, boot, labor added to existing bid. Updated total and margin displayed.",
  },
  {
    command:
      "What tonnage do I need for a 2,000 square foot house in climate zone 4, average insulation, south-facing windows?",
    response:
      "Manual J estimate: approximately 3.0–3.5 tons cooling capacity. Recommends field verification with actual load calculation before final equipment selection.",
  },
];

const faqs: FAQ[] = [
  {
    question: "Can Pilot handle seasonal dispatch volume?",
    answer:
      "Yes. Pilot's dispatch board is built for exactly this — route techs by location, manage appointment windows, handle callbacks, and auto-notify customers with real-time ETAs. When June hits and the calls pile up, Pilot keeps the schedule organized so you can focus on the work.",
  },
  {
    question: "Does it know real equipment pricing?",
    answer:
      "Pilot tracks current pricing for major HVAC manufacturers — condensers, air handlers, furnaces, mini-splits, line sets, and common components. When you build a bid, the equipment costs are current, not pulled from a price sheet you printed last quarter.",
  },
  {
    question: "Can I build a full system replacement bid by voice?",
    answer:
      "Absolutely. Describe the system — tonnage, model, ductwork scope, electrical, accessories — and Pilot generates the full bid. Equipment, materials, labor, permit, disposal. A bid that takes 2–3 hours manually takes about 10 minutes.",
  },
  {
    question: "What about load calculations?",
    answer:
      "Pilot provides Manual J estimation references to help you size equipment quickly in the field. It's designed to assist your professional judgment, not replace a full engineering calculation. Use it for quick field estimates, then verify with your preferred load calc tool for final equipment selection.",
  },
  {
    question: "Does it sync with QuickBooks?",
    answer:
      "Bi-directional QuickBooks Online sync. Invoices, payments, and customer records push automatically. When a system install is invoiced in Pilot, it shows up in QuickBooks without you touching it. Your bookkeeper stays happy.",
  },
  {
    question: "I'm on rooftops and in attics all day. What about signal?",
    answer:
      "Pilot works offline. Create bids, log time, take photos of existing equipment — everything queues and syncs when you're back in range. Built for rooftops, attics, crawl spaces, and mechanical rooms with zero bars.",
  },
  {
    question: "My shop is just me and one helper. Is this too much?",
    answer:
      "It's built for exactly that. Solo operators and small crews lose the most time to admin because there's no office staff. Pilot is $49/month, everything included, with unlimited users. Pilot is the office you don't have — it handles the quoting and paperwork so you handle the installs.",
  },
];

export default async function HvacTradePage() {
  const { mode } = await getSiteMode();
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <TradePageTemplate
        trade="hvac"
        accentToken="--trade-hvac"
        heroBadge="Built for HVAC Contractors"
        heroHeadline="The AI Copilot for HVAC Contractors"
        heroSubheadline="Summer hits and your phone explodes. Pilot handles the quoting, dispatch, and customer updates so you can focus on the installs — not the inbox."
        heroImageAlt="HVAC tech on rooftop next to commercial unit using Pilot quoting interface on phone"
        painSectionHeading="The Business Side of HVAC Is Brutal"
        painSectionSubtitle="You can size a system in your sleep. It's the quoting, scheduling, and invoicing that eat your margins alive."
        painPoints={painPoints}
        featureSectionHeading="What Pilot Does for HVAC Contractors"
        featureSectionSubtitle="The tools your business needs — designed for how HVAC techs actually work in the field."
        features={features}
        voiceSectionHeading="Pilot Speaks HVAC"
        voiceSectionSubtitle="Not a generic CRM that doesn't know a SEER rating from a serial number."
        voiceExamples={voiceExamples}
        voiceBodyCopy="Pilot's Voice AI understands HVAC terminology — equipment model numbers, SEER ratings, refrigerant types, and common manufacturer catalogs. It builds bids the way you think about systems, not the way a generic form does."
        pricingSectionHeading="Built for Your HVAC Business"
        pricingBodyCopy="$49/month, everything included. Quoting, dispatch, invoicing, profitability tracking, and QuickBooks sync — one platform that handles peak season as well as you do. Saves 15+ hours per week in admin time. That's another install on the schedule every week."
        faqSectionHeading="Common Questions from HVAC Contractors"
        faqs={faqs}
        finalCtaHeadline="Join the HVAC Contractors Shaping Pilot"
        finalCtaBody="Pilot for Trades is built with input from real HVAC contractors. Be one of the first twelve, lock in Charter pricing, and help shape the tool that handles your peak season — so you don't have to do it from a clipboard."
        siteMode={mode}
      />
    </>
  );
}
