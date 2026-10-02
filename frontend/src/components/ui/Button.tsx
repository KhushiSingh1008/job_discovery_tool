import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";

import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

function buttonClass(variant: ButtonVariant = "secondary", size: ButtonSize = "md") {
  return [styles.button, styles[variant], styles[size]].join(" ");
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
}

export function Button({
  variant,
  size,
  icon,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={`${buttonClass(variant, size)} ${className ?? ""}`} {...rest}>
      {icon}
      {children}
    </button>
  );
}

interface LinkButtonProps extends LinkProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function LinkButton({ variant, size, className, ...rest }: LinkButtonProps) {
  return <Link className={`${buttonClass(variant, size)} ${className ?? ""}`} {...rest} />;
}
