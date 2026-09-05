import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, CheckCircle2, XCircle, ArrowRight } from "lucide-react"
import { exchangeUpstoxCode } from "@/api"

export default function Callback() {
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [message, setMessage] = useState("Exchanging OAuth code for access token...")

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get("code")
    const errorParam = params.get("error")
    if (errorParam) {
      setStatus("error")
      setMessage(`Upstox returned an error: ${errorParam}`)
      return
    }
    if (!code) {
      setStatus("error")
      setMessage("No OAuth code found in callback URL.")
      return
    }
    const redirect_uri = `${window.location.origin}/callback`
    exchangeUpstoxCode(code, redirect_uri)
      .then(r => {
        setStatus("success")
        setMessage(`Token stored (length ${r.token_length}). Redirecting to portfolio...`)
        setTimeout(() => { window.location.href = "/portfolio" }, 1500)
      })
      .catch(e => {
        setStatus("error")
        setMessage(`OAuth exchange failed: ${e.message}`)
      })
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <Card className="max-w-md w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {status === "loading" && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
            {status === "success" && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
            {status === "error" && <XCircle className="h-5 w-5 text-rose-500" />}
            Upstox OAuth
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{message}</p>
          {status === "error" && (
            <Button variant="outline" onClick={() => { window.location.href = "/portfolio" }}>
              Back to Portfolio <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
