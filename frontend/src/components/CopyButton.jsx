import React, { useState } from "react";
export default function CopyButton({ text }){
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text || ""); setCopied(true); setTimeout(()=>setCopied(false), 1500); }
    catch { alert("Could not copy to clipboard"); }
  };
  if (!text) return null;
  return <button onClick={copy} className="btn-secondary" title="Copy link">{copied ? "Copied!" : "Copy"}</button>;
}