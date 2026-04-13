import { motion } from "framer-motion";

interface WinProbRingProps {
  probability: number;
  size?: number;
  label?: string;
}

export default function WinProbRing({ probability, size = 200, label }: WinProbRingProps) {
  const radius = (size / 2) - 16;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  return (
    <div className="relative flex flex-col items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke="currentColor"
          strokeWidth="10"
          fill="transparent"
          className="text-secondary"
        />
        <motion.circle
          cx={center}
          cy={center}
          r={radius}
          stroke="currentColor"
          strokeWidth="10"
          fill="transparent"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - (circumference * probability) / 100 }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
          strokeLinecap="butt"
          className="text-primary"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-4xl font-bold tracking-tighter animate-pulse-slow">
          {probability}%
        </span>
        {label && (
          <span className="text-xs text-muted-foreground mt-1 uppercase tracking-widest">{label}</span>
        )}
      </div>
    </div>
  );
}
