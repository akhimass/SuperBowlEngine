import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Activity, BarChart3, Brain, FileText, FlaskConical, Shield, Target, TrendingUp, Zap } from "lucide-react";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import Navbar from "@/components/layout/Navbar";
import { Button } from "@/components/ui/button";
import { runBacktest } from "@/lib/api";
import ExamplePredictionCard from "@/components/ExamplePredictionCard";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.3 } },
};
const item = {
  hidden: { y: 16, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { ease: [0.16, 1, 0.3, 1] as [number, number, number, number], duration: 0.7 } },
};

const modules = [
  {
    title: "Matchup Engine",
    description: "Predicts game outcomes using opponent-adjusted offensive and defensive efficiency metrics.",
    icon: Target,
    badge: "Core",
    badgeClass: "pill-offense",
  },
  {
    title: "Super Bowl Engine",
    description: "Championship-caliber prediction model and flagship analytical showcase.",
    icon: Zap,
    badge: "Flagship",
    badgeClass: "pill-qb",
  },
  {
    title: "QB Production Engine",
    description: "Evaluates quarterback impact beyond box scores using EPA, CPOE, and situational splits.",
    icon: Brain,
    badge: "Advanced",
    badgeClass: "pill-offense",
  },
  {
    title: "Scouting Report Generator",
    description: "Creates readable, coach-style football breakdowns from raw statistical data.",
    icon: FileText,
    badge: "Intel",
    badgeClass: "pill-defense",
  },
  {
    title: "Backtest Engine",
    description: "Compares model predictions against historical NFL results for calibration and transparency.",
    icon: FlaskConical,
    badge: "Validation",
    badgeClass: "pill-neutral",
  },
];

export default function LandingPage() {
  const { data } = useQuery({
    queryKey: ["landing-backtest"],
    queryFn: () => runBacktest(2024),
  });

  const stats = useMemo(() => {
    if (!data) {
      return [
        { value: "—", label: "Backtested Accuracy" },
        { value: "—", label: "Avg Score Error (pts)" },
        { value: "—", label: "Games Analyzed" },
        { value: "5", label: "Analytical Engines" },
      ];
    }
    const accuracyPct = `${Math.round(data.accuracy * 1000) / 10}%`;
    const avgErr = data.average_score_error.toFixed(1);
    const games = data.calibration_data.length.toString();
    return [
      { value: accuracyPct, label: "Backtested Accuracy" },
      { value: avgErr, label: "Avg Score Error (pts)" },
      { value: games, label: "Games Analyzed" },
      { value: "5", label: "Analytical Engines" },
    ];
  }, [data]);
  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <section className="pt-28 pb-20 px-4">
        <div className="container max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
          >
            <div className="inline-flex items-center gap-2 pill-neutral mb-6">
              <Activity className="h-3 w-3" />
              <span>AI-Powered NFL Intelligence Platform</span>
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tighter leading-[0.95] text-gradient-hero mb-6">
              NFL Matchup Intelligence,
              <br />
              Scouting Reports &
              <br />
              Predictive Game Analysis
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8 leading-relaxed">
              Transforming play-by-play data into opponent-adjusted team evaluations,
              coach-style scouting reports, and explainable football insights.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button asChild size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-sm font-semibold px-8">
                <Link to="/matchup">Run a Matchup</Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="rounded-sm border-border text-foreground hover:bg-secondary px-8">
                <Link to="/schedule">Explore Schedule</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Example prediction + stats */}
      <section className="border-y border-border py-10 bg-card/40">
        <div className="container max-w-5xl mx-auto grid gap-8 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] items-stretch">
          <div className="order-2 md:order-1">
            <motion.div
              variants={container}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="grid grid-cols-2 md:grid-cols-2 gap-6"
            >
              {stats.map((s) => (
                <motion.div key={s.label} variants={item} className="text-left">
                  <div className="font-mono text-2xl md:text-3xl font-bold tracking-tight">{s.value}</div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">{s.label}</div>
                </motion.div>
              ))}
            </motion.div>
          </div>
          <div className="order-1 md:order-2">
            <ExamplePredictionCard />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-4">
        <div className="container max-w-5xl mx-auto space-y-10">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center"
          >
            <h2 className="text-3xl font-bold tracking-tighter mb-3">How GridironIQ Works</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              A layered engine that turns raw play-by-play into matchup predictions, coach-style scouting reports, and
              historical validation.
            </p>
          </motion.div>

          <motion.div
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            className="grid md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {modules.map((mod) => (
              <motion.div
                key={mod.title}
                variants={item}
                className="card-surface rim-light p-6 hover:border-primary/30 transition-colors group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="p-2 rounded-sm bg-secondary">
                    <mod.icon className="h-5 w-5 text-foreground" />
                  </div>
                  <span className={mod.badgeClass}>{mod.badge}</span>
                </div>
                <h3 className="text-lg font-semibold tracking-tight mb-2">{mod.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{mod.description}</p>
              </motion.div>
            ))}
          </motion.div>

          <motion.div
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            className="grid md:grid-cols-2 gap-8 border-t border-border pt-10"
          >
            {[
              {
                icon: Target,
                title: "Matchup Predictor",
                desc: "Run any matchup from 2020–2025 with opponent-adjusted team profiles and projected scores.",
              },
              {
                icon: FileText,
                title: "Scouting Reports",
                desc: "Executive-style breakdowns of offensive, defensive, and situational edges for each game.",
              },
              {
                icon: TrendingUp,
                title: "Historical Validation",
                desc: "Backtested against recent NFL seasons with accuracy, score error, and calibration views.",
              },
              {
                icon: Shield,
                title: "AI Statistician",
                desc: "Grounded AI layer that explains why the model leans one way and what could flip the result.",
              },
            ].map((f) => (
              <motion.div key={f.title} variants={item} className="flex gap-4">
                <div className="shrink-0 p-2.5 rounded-sm bg-secondary h-fit">
                  <f.icon className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <h3 className="font-semibold tracking-tight mb-1">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4">
        <div className="container flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-primary" />
            <span className="font-semibold text-foreground">GridironIQ</span>
          </div>
          <span>NFL Matchup Intelligence Platform</span>
        </div>
      </footer>
    </div>
  );
}
