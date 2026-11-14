# IP & Open-Source Licensing — posture

*Where the code came from, who owns it, and how third-party licenses were kept clean. Capability evidence that I think about IP hygiene the way an architect should — as a design constraint from day one, not a cleanup task before a deal. This is my posture and understanding, not legal advice; a formal license scan is the verification step named below.*

---

## Ownership of the AI-authored code
The application code was **AI-authored under my direction**, and I treat it as **mine to own and license.** As I read the terms I used them under, the major LLM providers in the build (Anthropic, OpenAI, Google, xAI) assign ownership of model *output* to the user, with no shared-ownership or disclosure obligation attaching to the generated code. Terms vary by provider, plan and date, and I have not had every model's terms (including Kimi and GLM) reviewed by counsel. I directed, reviewed, and accepted every change, so there is a single human owner of record. One honest caveat: copyright protection for largely AI-generated work is still an unsettled area (the U.S. Copyright Office's current position is that protection extends to the human-authored contribution), so this is my understanding of the ownership chain, not a legal opinion.

## This repository's license
Published under a **source-available Evaluation & Portfolio License — all rights reserved** (`LICENSE`). It's viewable as a capability demonstration; it is **not** granted for commercial use, redistribution, or derivative works. The repository is a proof asset, not an open-source project.

## Third-party open-source dependencies
- **Mainstream, permissive stack.** Backend rests on FastAPI, SQLAlchemy, Pydantic, Celery, boto3, Alembic (MIT / BSD / Apache-2.0); frontend on React, Next.js, Expo/React Native, TanStack Query (MIT). These are among the most widely-vetted licenses in commercial software.
- **Backend fully pinned** — every backend dependency is pinned with `==` (`requirements.txt`), so the dependency set is deterministic and auditable rather than floating.
- **No strong copyleft** — the backend requirements include no GPL or AGPL packages. Two weak-copyleft dependencies are used unmodified as libraries: `psycopg2-binary` (LGPL) and `certifi` (MPL-2.0). As I understand it, that places no obligation on the application code; the SBOM and licence report below is the verification step.
- **NEC reference values** — `backend/services/nec_service.py` cites a minimal subset of NEC 2023 table values (with an NFPA attribution note). They have not had a licensing review.

## The verification step (named, not yet run as a formal artifact)
Before any commercial use or distribution, the clean formal step is a **generated SBOM + license report** — e.g. `pip-licenses` for Python and `license-checker` for the JS workspaces — attached as an artifact. The posture above is high-confidence from the dependency set; the SBOM is what turns "confident" into "attested." *(Aspirational artifact; the pinned, permissive dependency set is the implemented reality.)*

## What this demonstrates
Clean IP is a precondition most technical founders discover late — in a diligence or acquisition conversation they're unprepared for. Here, there is one human owner of record, the license is explicit, the dependencies are permissive or weak-copyleft and pinned, and the remaining formalizations (the SBOM and a counsel review) are named rather than assumed. Thinking about this on day one, not day 400, is part of what I bring.
