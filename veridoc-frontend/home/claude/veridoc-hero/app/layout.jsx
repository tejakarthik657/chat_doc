import { DM_Serif_Display } from 'next/font/google'

const dmSerif = DM_Serif_Display({
  subsets: ['latin'],
  weight: ['400'],
  style: ['normal', 'italic'],
  variable: '--font-serif',
  display: 'swap',
})

export const metadata = {
  title: 'Veridoc',
  description: 'Source-grounded document intelligence.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={dmSerif.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&display=swap"
          rel="stylesheet"
        />
        {/* Satoshi from CDN */}
        <link
          href="https://api.fontshare.com/v2/css?f[]=satoshi@300,400,500,700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ margin: 0, padding: 0, background: '#02020A', overflowX: 'hidden', cursor: 'none' }}>
        <style>{`
          *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

          ::selection {
            background: rgba(0,255,136,0.25);
            color: #F0F0F5;
          }

          ::-webkit-scrollbar { width: 4px; }
          ::-webkit-scrollbar-track { background: #02020A; }
          ::-webkit-scrollbar-thumb { background: #1A2A1A; border-radius: 2px; }
          ::-webkit-scrollbar-thumb:hover { background: #00FF88; }

          @keyframes fadeUp {
            from { opacity: 0; transform: translateY(20px); }
            to   { opacity: 1; transform: translateY(0); }
          }

          @keyframes feedPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50%       { opacity: 0.25; transform: scale(0.75); }
          }

          @keyframes scrollPulse {
            0%   { opacity: 0; transform: scaleY(0.1); transform-origin: top; }
            50%  { opacity: 1; transform: scaleY(1);   transform-origin: top; }
            100% { opacity: 0; transform: scaleY(1);   transform-origin: bottom; }
          }

          @keyframes marqueeScroll {
            from { transform: translateX(0); }
            to   { transform: translateX(-50%); }
          }

          @keyframes shimmer {
            from { background-position: -200% 0; }
            to   { background-position:  200% 0; }
          }

          /* Grain overlay */
          body::after {
            content: '';
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 9000;
            opacity: 0.022;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
            background-repeat: repeat;
            background-size: 128px 128px;
          }
        `}</style>
        {children}
      </body>
    </html>
  )
}
