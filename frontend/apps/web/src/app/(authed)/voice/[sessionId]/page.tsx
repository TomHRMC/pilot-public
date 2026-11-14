import { VoiceSessionDetailPage } from "@/features/voice/components/VoiceSessionDetailPage";

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function VoiceSessionDetailRoute({ params }: Props) {
  const { sessionId } = await params;
  return <VoiceSessionDetailPage sessionId={sessionId} />;
}
