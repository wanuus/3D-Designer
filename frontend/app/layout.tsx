import "./globals.css";
import Shell from "@/components/Shell";
export const metadata = { title: "Interior Studio" };
const themeScript = `try{var t=localStorage.getItem('ais-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.classList.toggle('dark',t==='dark')}catch(e){}`;
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body><Shell>{children}</Shell></body>
    </html>
  );
}
