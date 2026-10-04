import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";

import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "icon";
export type ButtonSize = "sm" | "md" | "lg";

function buttonClass(variant: ButtonVariant = "secondary", size: ButtonSize = "md") {
  return [styles.button, styles[variant], variant === "icon" ? "" : styles[size]].join(" ");
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

interface ExternalLinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/** A button-styled link to another site; always opens in a new tab. */
export function ExternalLinkButton({ variant, size, className, ...rest }: ExternalLinkButtonProps) {
  return (
    <a
      className={`${buttonClass(variant, size)} ${className ?? ""}`}
      target="_blank"
      rel="noreferrer"
      {...rest}
    />
  );
}
