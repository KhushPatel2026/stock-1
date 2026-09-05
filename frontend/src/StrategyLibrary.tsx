import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fetchStrategies } from "@/api"
import type { Strategy } from "@/api"

const FAMILY_COLORS: Record<string, string> = {
  Trend: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
  MR: "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20",
  Momentum: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  Factor: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  Volume: "bg-orange-500/10 text-orange-700 dark:text-orange-300 border-orange-500/20",
  Pattern: "bg-pink-500/10 text-pink-700 dark:text-pink-300 border-pink-500/20",
  Volatility: "bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/20",
  Options: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-500/20",
  Event: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/20",
  Stat_arb: "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/20",
  Cross_sect: "bg-lime-500/10 text-lime-700 dark:text-lime-300 border-lime-500/20",
  Hedge: "bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/20",
  ML: "bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300 border-fuchsia-500/20",
  Allocation: "bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-500/20",
  Carry: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300 border-yellow-500/20",
  Other: "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20",
}

export default function StrategyLibrary() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [search, setSearch] = useState("")
  const [familyFilter, setFamilyFilter] = useState<string>("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch(e => setError(e.message))
  }, [])

  const families = Array.from(new Set(strategies.map(s => s.family))).sort()
  const filtered = strategies.filter(s => {
    if (familyFilter && s.family !== familyFilter) return false
    if (search && !(`${s.name} ${s.id} ${s.description}`.toLowerCase().includes(search.toLowerCase()))) return false
    return true
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Strategy Library ({strategies.length})</CardTitle>
        <CardDescription>Browse all {strategies.length} registered strategies across {families.length} families.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col md:flex-row gap-2 mb-4">
          <Input
            placeholder="Search strategies..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="md:max-w-sm"
          />
          <div className="flex flex-wrap gap-1">
            <Badge
              variant={familyFilter === "" ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setFamilyFilter("")}
            >
              All
            </Badge>
            {families.map(f => (
              <Badge
                key={f}
                variant={familyFilter === f ? "default" : "outline"}
                className={`cursor-pointer ${familyFilter === f ? "" : FAMILY_COLORS[f] || FAMILY_COLORS.Other}`}
                onClick={() => setFamilyFilter(familyFilter === f ? "" : f)}
              >
                {f} ({strategies.filter(s => s.family === f).length})
              </Badge>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-48">Strategy</TableHead>
              <TableHead className="w-32">Family</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="w-64">Default Params</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map(s => (
              <TableRow key={s.id}>
                <TableCell className="font-medium">{s.name}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={FAMILY_COLORS[s.family] || FAMILY_COLORS.Other}>
                    {s.family}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{s.description}</TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">
                  {JSON.stringify(s.params)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {filtered.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">No strategies match.</p>
        )}
      </CardContent>
    </Card>
  )
}
