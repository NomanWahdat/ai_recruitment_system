"use client";
import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";
export function Modal({open,title,onClose,children}:{open:boolean;title:string;onClose:()=>void;children:ReactNode}) {
  const ref=useRef<HTMLDivElement>(null);const id=useId();
  const closeRef=useRef(onClose);
  useEffect(()=>{closeRef.current=onClose;},[onClose]);
  useEffect(()=>{
    if(!open)return;
    const previous=document.activeElement as HTMLElement|null;
    const first=()=>ref.current?.querySelector<HTMLElement>("button,input,select,textarea,a[href]");
    first()?.focus();
    const handler=(event:KeyboardEvent)=>{
      if(event.key==="Escape"){event.preventDefault();closeRef.current();}
      if(event.key==="Tab"){
        const nodes=Array.from(ref.current?.querySelectorAll<HTMLElement>("button:not([disabled]),input,select,textarea,a[href]")||[]);
        const start=nodes[0],end=nodes[nodes.length-1];
        if(event.shiftKey&&document.activeElement===start){event.preventDefault();end?.focus();}
        else if(!event.shiftKey&&document.activeElement===end){event.preventDefault();start?.focus();}
      }
    };
    const overflow=document.body.style.overflow;document.body.style.overflow="hidden";
    document.addEventListener("keydown",handler);
    return ()=>{document.removeEventListener("keydown",handler);document.body.style.overflow=overflow;previous?.focus();};
  },[open]);
  if(!open)return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
    <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={id} className="w-full max-w-3xl rounded-3xl bg-white shadow-2xl">
      <div className="flex items-center justify-between border-b px-6 py-4"><h2 id={id} className="text-lg font-semibold">{title}</h2>
        <button type="button" aria-label="Close dialog" onClick={onClose} className="rounded-lg border px-3 py-2">Close</button></div>
      <div className="max-h-[80vh] overflow-y-auto p-6">{children}</div>
    </div>
  </div>;
}
