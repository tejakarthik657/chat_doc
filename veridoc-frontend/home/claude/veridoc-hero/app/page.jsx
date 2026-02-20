import HeroSection from '@/components/HeroSection'
import CustomCursor from '@/components/CustomCursor'

export const metadata = {
  title: 'Veridoc — Your Documents. Finally, Honest Answers.',
  description: 'Source-grounded document intelligence. Every answer has a page number. Zero hallucinations.',
}

export default function Home() {
  return (
    <main style={{ background: '#02020A', minHeight: '100vh' }}>
      <CustomCursor />
      <HeroSection />
    </main>
  )
}
