
import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export function Card({ className, children }) {
    return (
        <div className={cn("bg-white rounded-lg border border-slate-200 shadow-sm", className)}>
            {children}
        </div>
    );
}

export function CardHeader({ className, children }) {
    return (
        <div className={cn("p-6 pb-2", className)}>
            {children}
        </div>
    );
}

export function CardTitle({ className, children }) {
    return (
        <h3 className={cn("text-lg font-semibold leading-none tracking-tight", className)}>
            {children}
        </h3>
    );
}

export function CardContent({ className, children }) {
    return (
        <div className={cn("p-6 pt-0", className)}>
            {children}
        </div>
    );
}
