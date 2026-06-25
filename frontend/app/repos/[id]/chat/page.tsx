"use client";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { ChatPanel } from "@/components/chat/chat-panel";

export default function ChatPage({ params }: { params: { id: string } }) {
  return <ProtectedRoute><main className="min-h-screen bg-aurora px-6 py-10"><div className="mx-auto max-w-4xl"><ChatPanel repositoryId={Number(params.id)} /></div></main></ProtectedRoute>;
}