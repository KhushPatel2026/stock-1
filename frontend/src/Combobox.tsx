import * as React from "react"
import { Check, ChevronsUpDown, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

export interface ComboboxOption {
  value: string
  label: string
  hint?: string
}

interface Props {
  options: ComboboxOption[]
  value: string[]
  onChange: (v: string[]) => void
  placeholder?: string
  multi?: boolean
  emptyMessage?: string
  className?: string
}

export function Combobox({ options, value, onChange, placeholder = "Select...", multi = false, emptyMessage = "No matches.", className }: Props) {
  const [open, setOpen] = React.useState(false)

  const toggle = (v: string) => {
    if (multi) {
      onChange(value.includes(v) ? value.filter(x => x !== v) : [...value, v])
    } else {
      onChange([v])
      setOpen(false)
    }
  }

  const remove = (v: string) => {
    onChange(value.filter(x => x !== v))
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex min-h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background hover:bg-accent/30 focus:outline-none focus:ring-2 focus:ring-ring",
            className
          )}
        >
          <div className="flex flex-wrap gap-1 items-center flex-1 text-left">
            {value.length === 0 && <span className="text-muted-foreground">{placeholder}</span>}
            {value.length > 0 && multi && value.slice(0, 3).map(v => {
              const opt = options.find(o => o.value === v)
              return (
                <Badge key={v} variant="secondary" className="gap-1">
                  {opt?.label ?? v}
                  <X className="h-3 w-3 cursor-pointer" onClick={(e) => { e.stopPropagation(); remove(v) }} />
                </Badge>
              )
            })}
            {value.length > 3 && multi && <Badge variant="secondary">+{value.length - 3} more</Badge>}
            {value.length > 0 && !multi && (
              <span>{options.find(o => o.value === value[0])?.label ?? value[0]}</span>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command>
          <CommandInput placeholder={`Search ${options.length}...`} />
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup>
              {options.map(opt => (
                <CommandItem
                  key={opt.value}
                  value={opt.value}
                  onSelect={() => toggle(opt.value)}
                >
                  <Check className={cn("mr-2 h-4 w-4", value.includes(opt.value) ? "opacity-100" : "opacity-0")} />
                  <div className="flex flex-col">
                    <span>{opt.label}</span>
                    {opt.hint && <span className="text-xs text-muted-foreground">{opt.hint}</span>}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
