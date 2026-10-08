// Standalone public page (/estimate): its own small bundle, no login shell.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/montserrat/400.css'
import '@fontsource/montserrat/600.css'
import '@fontsource/montserrat/700.css'
import './estimate.css'
import Estimate from './Estimate'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Estimate apiBase="" />
  </StrictMode>,
)
