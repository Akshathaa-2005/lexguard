'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowLeft, Download, Search } from 'lucide-react'
import axios from 'axios'

type PolicyBrowseItem = {
  document_id: string
  document_name?: string
  country?: string
  publish_date?: string
}

const countries = ['Europe', 'Australia', 'USA', 'India']
const domains = ['AI', 'Healthcare', 'Fintech', 'Crypto', 'Biotech', 'Consumer Apps', 'Insurance']

export default function ExplorePolicyPage() {
  const [browseCountry, setBrowseCountry] = useState('')
  const [browseDomain, setBrowseDomain] = useState('')
  const [browseResults, setBrowseResults] = useState<PolicyBrowseItem[]>([])
  const [isBrowsing, setIsBrowsing] = useState(false)
  const [browseError, setBrowseError] = useState('')

  const handleBrowse = async () => {
    if (!browseCountry && !browseDomain) {
      setBrowseError('Select at least a country or domain')
      return
    }

    setIsBrowsing(true)
    setBrowseError('')
    setBrowseResults([])

    try {
      const params: Record<string, string> = {}
      if (browseCountry) params.country = browseCountry
      if (browseDomain) params.domain = browseDomain
      const res = await axios.get<{ documents?: PolicyBrowseItem[] }>('http://localhost:5000/policies', { params })
      setBrowseResults(res.data.documents || [])
      if ((res.data.documents || []).length === 0) {
        setBrowseError('No policies found for this selection')
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const message = (err.response?.data as { error?: string } | undefined)?.error
        setBrowseError(message || 'Failed to fetch policies')
      } else {
        setBrowseError('Failed to fetch policies')
      }
    } finally {
      setIsBrowsing(false)
    }
  }

  const downloadPolicy = async (documentId: string, policyName: string) => {
    try {
      const response = await axios.get(`http://localhost:5000/policy/${documentId}`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `policy_${policyName.replace(/\s+/g, '_')}.txt`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      setBrowseError('Failed to download selected policy')
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-[#f8fbf8] via-white to-[#edf5ed] px-4 py-8 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 rounded-3xl border border-[#d7e5d6] bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="mb-2 inline-flex rounded-full bg-[#edf5ed] px-3 py-1 text-xs font-semibold text-[#3f6b4b]">
                Policy Search Workspace
              </p>
              <h1 className="text-2xl font-bold text-slate-900">Explore Policy</h1>
              <p className="mt-1 text-sm text-slate-600">Search policy documents by geography and domain, then download full text.</p>
            </div>
            <Link
              href="/"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#b8cfb9] bg-[#eef6ee] px-4 py-2 text-sm font-semibold text-[#325b3d] transition hover:bg-[#e1efe2]"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Upload Project
            </Link>
          </div>
        </header>

        <section className="rounded-3xl border border-[#d7e5d6] bg-white p-6 shadow-sm">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <select
              value={browseCountry}
              onChange={(e) => setBrowseCountry(e.target.value)}
              className="rounded-xl border border-[#d5e2d4] bg-white p-3 text-sm outline-none transition focus:border-[#8eb490]"
            >
              <option value="">All Countries</option>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
            <select
              value={browseDomain}
              onChange={(e) => setBrowseDomain(e.target.value)}
              className="rounded-xl border border-[#d5e2d4] bg-white p-3 text-sm outline-none transition focus:border-[#8eb490]"
            >
              <option value="">All Domains</option>
              {domains.map((domain) => (
                <option key={domain} value={domain}>
                  {domain}
                </option>
              ))}
            </select>
            <button
              onClick={handleBrowse}
              disabled={isBrowsing}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#4e7d5a] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#3f6b4b] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Search className="h-4 w-4" />
              {isBrowsing ? 'Searching...' : 'Browse Policies'}
            </button>
          </div>

          {browseError && (
            <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{browseError}</p>
          )}

          <div className="mt-5 space-y-3">
            {browseResults.map((doc, i) => (
              <div key={i} className="rounded-2xl border border-[#e1ece0] bg-[#f9fcf9] p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{doc.document_name || doc.document_id}</p>
                    <p className="text-xs text-slate-500">
                      {doc.country} | {doc.publish_date}
                    </p>
                  </div>
                  <button
                    onClick={() => downloadPolicy(doc.document_id, doc.document_name || doc.document_id)}
                    className="inline-flex items-center gap-2 rounded-lg bg-[#eef6ee] px-3 py-2 text-xs font-semibold text-[#325b3d] hover:bg-[#e1efe2]"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
