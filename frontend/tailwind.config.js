/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'vbl-red': '#E30613',
                'vbl-grey': '#58585A',
                'vbl-light-grey': '#F4F4F4',
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
            }
        },
    },
    plugins: [],
}
