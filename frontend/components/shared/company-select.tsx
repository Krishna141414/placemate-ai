"use client";

import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCompanies } from "@/lib/companies";
import type { Company } from "@/lib/types";

const ORDER: Company["category"][] = ["Dream", "Standard", "Regular"];

export function CompanySelect({
  value,
  onChange,
  id,
  placeholder = "Choose a company",
  disabled,
  className,
  ...rest
}: {
  value: string | undefined;
  onChange: (id: string) => void;
  id?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
} & { "data-tour"?: string }) {
  const { companies } = useCompanies();
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled || !companies}>
      <SelectTrigger id={id} className={className ?? "w-full sm:w-80"} data-tour={rest["data-tour"]}>
        <SelectValue placeholder={companies ? placeholder : "Loading companies…"} />
      </SelectTrigger>
      <SelectContent>
        {ORDER.map((category) => {
          const group = (companies ?? []).filter((company) => company.category === category);
          if (!group.length) return null;
          return (
            <SelectGroup key={category}>
              <SelectLabel>{category}</SelectLabel>
              {group.map((company) => (
                <SelectItem key={company.id} value={company.id}>
                  {company.name}
                  <span className="ml-2 text-muted-foreground">{company.ctc_label}</span>
                </SelectItem>
              ))}
            </SelectGroup>
          );
        })}
      </SelectContent>
    </Select>
  );
}
