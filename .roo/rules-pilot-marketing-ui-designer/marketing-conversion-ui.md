# 🚀 Marketing & Conversion UI: Design Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Above the Fold" Mandate
Every landing page must instantly communicate value before the user scrolls.
* **Clear Value Proposition**: The H1 must state exactly what Pilot does for electrical contractors.
* **Primary Call to Action (CTA)**: A highly visible "Start Free Trial" or "Sign Up" button must be present immediately in the hero section and sticky in the top navigation.
* **Hero Imagery**: Use high-quality, relatable imagery (e.g., a contractor using a phone on a job site) rather than abstract tech graphics.


## 2. Visual Hierarchy & Scannability
Contractors are busy. The site must be scannable.
* **F-Pattern Layouts**: Design text and image blocks that follow natural eye movement.
* **Feature Chunks**: Break down complex features (QuickBooks sync, Voice Quoting) into alternating left/right blocks with brief text and clear UI screenshots.
* **White Space**: Use generous padding and margins (from the established spacing scale) to let elements breathe and draw attention to CTAs.

## 3. Trust & Social Proof
The design must build immediate credibility for trades businesses.
* **Testimonial Blocks**: Design dedicated, visually distinct sections for customer quotes, star ratings, and trade affiliations.
* **Security & Reliability Badges**: Visually highlight uptime, offline reliability, and secure data syncing.

## 4. Performance & SEO Structure
A beautiful site must also be fast and searchable.
* **Semantic HTML**: Strictly use proper `header`, `main`, `section`, `article`, and semantic heading tags (`H1` through `H6`) for SEO.
* **Image Optimization**: Ensure all image placeholders or implementations utilize modern formats (WebP/AVIF) and Next.js `<Image />` components where applicable.
