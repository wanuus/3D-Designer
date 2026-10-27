"use client";
export const ErrorNote = ({ msg }: { msg: string | null }) => msg ? <p role="alert" className="text-sm text-danger border border-danger/40 rounded px-3 py-2 my-2">{msg}</p> : null;
export const Empty = ({ children }: { children: React.ReactNode }) => <div className="panel p-8 text-center text-sm text-muted">{children}</div>;
export const Field = ({ label, children }: { label: string; children: React.ReactNode }) => <label className="block"><span className="label">{label}</span>{children}</label>;
