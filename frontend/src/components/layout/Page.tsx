import { motion } from "motion/react";
import { useEffect, type ReactNode } from "react";

interface PageProps {
  title: string;
  children: ReactNode;
}

/** Sets the document title and fades the page in on navigation. */
export function Page({ title, children }: PageProps) {
  useEffect(() => {
    document.title = `${title} · GradGuide Jobs`;
  }, [title]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
