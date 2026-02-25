import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Eye, Shield } from "lucide-react";
import { useEffect, useState } from "react";
import { getRiskLevelColor } from "@/lib/utils";

interface FraudScenario {
  id: string;
  name: string;
  description: string;
  riskLevel: "High" | "Medium-High" | "Medium" | "Low";
  enabled: boolean;
  priority: "Phase 1" | "Phase 2" | "Phase 3";
  keyIndicators: string[];
  commonUseCase: string;
  detailedDescription: string;
  disabled?: boolean; // For completely disabling scenarios from UI
}

const fraudScenarios: FraudScenario[] = [];

const Scenarios = () => {
  const [scenarios, setScenarios] = useState<FraudScenario[]>(fraudScenarios);

  useEffect(() => {
    const loadRules = async () => {
      try {
        const res = await fetch("/api/fraud/rules", { cache: "no-store" });
        if (!res.ok) return;
        const rules = await res.json();
        const sanitize = (arr: any): string[] =>
          Array.isArray(arr)
            ? arr.map((s) =>
                String(s)
                  .replace(/^.*key-indicators:/, "")
                  .trim()
              )
            : [];
        const mapped: FraudScenario[] = rules.map((r: any, idx: number) => ({
          id: r.name || `RULE_${idx + 1}`,
          name: r.name,
          description: r.description,
          riskLevel: "High",
          enabled: !!r.enabled,
          priority: "Phase 1",
          keyIndicators: sanitize(r.keyIndicators),
          commonUseCase: r.commonUseCase || "",
          detailedDescription: "",
        }));
        setScenarios(mapped);
      } catch (e) {
        console.error("Failed to load rules", e);
      }
    };
    loadRules();
  }, []);

  const toggleScenario = async (scenarioId: string) => {
    const target = scenarios.find((s) => s.id === scenarioId);
    if (!target) return;
    const nextEnabled = !target.enabled;
    setScenarios((prev) =>
      prev.map((s) =>
        s.id === scenarioId ? { ...s, enabled: nextEnabled } : s
      )
    );
    try {
      await fetch(`/api/fraud/rules/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: target.name, enabled: nextEnabled }),
      });
    } catch (e) {
      console.error("Failed to toggle rule", e);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center space-x-2">
            <Shield className="w-5 h-5" />
            <span>Real Time Fraud Scenarios</span>
          </span>
          <div className="flex items-center space-x-2">
            <Badge variant="secondary">
              {scenarios.filter((s) => s.enabled).length} of {scenarios.length}{" "}
              enabled
            </Badge>
          </div>
        </CardTitle>
        <CardDescription>
          Configure which fraud detection patterns to monitor in real-time
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          {scenarios.map((scenario) => (
            <Collapsible key={scenario.id} defaultOpen={!scenario.disabled}>
              <div
                className={`border rounded-lg ${
                  scenario.disabled
                    ? "opacity-50 bg-gray-50 dark:bg-gray-900"
                    : ""
                }`}
              >
                <CollapsibleTrigger asChild>
                  <div className="flex items-center justify-between w-full p-3 hover:bg-gray-50">
                    <div className="flex items-center space-x-3">
                      <div onClick={(e) => e.stopPropagation()}>
                        <Switch
                          checked={scenario.enabled}
                          onCheckedChange={() =>
                            !scenario.disabled && toggleScenario(scenario.id)
                          }
                          disabled={scenario.disabled}
                        />
                      </div>
                      <div className="text-left">
                        <div
                          className={`font-medium ${
                            scenario.disabled ? "text-gray-400" : ""
                          }`}
                        >
                          {scenario.name}
                          {scenario.disabled && (
                            <span className="ml-2 text-xs">(Coming Soon)</span>
                          )}
                        </div>
                        <div
                          className={`text-sm ${
                            scenario.disabled
                              ? "text-gray-400"
                              : "text-muted-foreground"
                          }`}
                        >
                          {scenario.description}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge
                        className={`${getRiskLevelColor(scenario.riskLevel)} ${
                          scenario.disabled ? "opacity-50" : ""
                        }`}
                      >
                        {scenario.riskLevel}
                      </Badge>
                      <div
                        className={`inline-flex items-center justify-center h-9 rounded-md px-3 text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground ${
                          scenario.disabled
                            ? "cursor-not-allowed opacity-50"
                            : "cursor-pointer"
                        }`}
                        tabIndex={scenario.disabled ? -1 : 0}
                        role="button"
                        aria-label="View scenario details"
                      >
                        <Eye className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="space-y-3 text-sm p-3">
                    <strong>Key Indicators:</strong>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      {scenario.keyIndicators.map((indicator, index) => (
                        <li key={index} className="text-muted-foreground">
                          {indicator}
                        </li>
                      ))}
                    </ul>
                    <strong>Common Use Case:</strong>
                    <p className="text-muted-foreground mt-1">
                      {scenario.commonUseCase}
                    </p>
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default Scenarios;
