import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  CalendarDays,
  FileText,
  Gauge,
  ListOrdered,
  Menu,
  Trophy,
  X,
} from "lucide-react";
import { useState } from "react";

const navItems = [
  { to: "/", label: "Home", icon: Activity },
  { to: "/matchup", label: "Matchup Engine", icon: BarChart3 },
  { to: "/schedule", label: "Schedule History", icon: CalendarDays },
  { to: "/accuracy", label: "Data Accuracy", icon: Gauge },
  { to: "/reports", label: "Report Library", icon: FileText },
  { to: "/draft", label: "Draft Room", icon: Trophy },
  { to: "/draft/simulator", label: "2026 Mock Draft", icon: ListOrdered },
];

export default function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="container flex h-14 items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-primary">
            <Activity className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold tracking-tight">GridironIQ</span>
        </Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`relative flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors rounded-sm ${
                  active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <item.icon className="h-3.5 w-3.5" />
                {item.label}
                {active && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="absolute inset-0 rounded-sm bg-secondary"
                    style={{ zIndex: -1 }}
                    transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
                  />
                )}
              </Link>
            );
          })}
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-2 text-muted-foreground"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:hidden border-t border-border bg-background px-4 py-3"
        >
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium rounded-sm ${
                location.pathname === item.to ? "text-foreground bg-secondary" : "text-muted-foreground"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </motion.div>
      )}
    </nav>
  );
}
