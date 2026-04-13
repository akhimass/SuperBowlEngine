import Navbar from "@/components/layout/Navbar";
import DraftSimulator from "./DraftSimulator";

/**
 * 2026 Round 1 mock draft simulator (static boards + AI-style projections).
 * Wrapped with app shell; simulator has its own full-width layout.
 */
export default function DraftSimulatorPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-14">
        <DraftSimulator />
      </main>
    </div>
  );
}
