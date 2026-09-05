import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"

export function ThemeToggle() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return true
    const saved = localStorage.getItem("stock1_theme")
    if (saved) return saved === "dark"
    return window.matchMedia("(prefers-color-scheme: dark)").matches || true
  })

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add("dark")
      localStorage.setItem("stock1_theme", "dark")
    } else {
      root.classList.remove("dark")
      localStorage.setItem("stock1_theme", "light")
    }
  }, [isDark])

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setIsDark(!isDark)}
      className="h-8 px-2.5 rounded-lg border-border/80 bg-background/50 backdrop-blur hover:bg-accent text-foreground/80 hover:text-foreground transition-all gap-1.5 text-xs font-medium"
      title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
    >
      {isDark ? (
        <>
          <Moon className="h-3.5 w-3.5 text-primary" />
          <span className="hidden sm:inline">Dark</span>
        </>
      ) : (
        <>
          <Sun className="h-3.5 w-3.5 text-amber-500" />
          <span className="hidden sm:inline">Light</span>
        </>
      )}
    </Button>
  )
}
