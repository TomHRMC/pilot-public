/**
 * GET /api/health
 *
 * Health check endpoint for the pilot-web ECS service (ALB target-group probe).
 * Returns HTTP 200 with a JSON body. This route is intentionally public (no auth)
 * so the load balancer's health probe can reach it without a Cognito JWT.
 */
export const dynamic = "force-dynamic";

export function GET(): Response {
  return Response.json({ status: "ok", service: "pilot-web" }, { status: 200 });
}
