"use client";

import { useState } from "react";
import { Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { AppRoute } from "@/lib/navigation";

import { Brand } from "./brand";
import { NavLinks } from "./nav-links";

export function MobileNav({ routes }: { routes: AppRoute[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-72 border-sidebar-border bg-sidebar px-3 py-5 text-sidebar-foreground"
      >
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <div className="mb-8 px-1">
          <Brand />
        </div>
        <NavLinks routes={routes} onNavigate={() => setOpen(false)} />
      </SheetContent>
    </Sheet>
  );
}
