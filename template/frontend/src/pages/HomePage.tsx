import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { healthcheck, submitQuery } from "@/lib/api";

export function HomePage() {
  const [input, setInput] = useState("");

  const health = useQuery({
    queryKey: ["healthcheck"],
    queryFn: healthcheck,
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: submitQuery,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      mutation.mutate(input);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Stackkit App</CardTitle>
          <CardDescription className="flex items-center gap-2">
            <span
              className={`inline-block size-2 rounded-full ${
                health.isSuccess
                  ? "bg-green-500"
                  : health.isError
                    ? "bg-red-500"
                    : "bg-yellow-500"
              }`}
            />
            {health.isSuccess
              ? "API connected"
              : health.isError
                ? "API unreachable"
                : "Checking API..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type something..."
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Sending..." : "Submit"}
            </Button>
          </form>

          {mutation.isSuccess && (
            <div className="mt-4 rounded-md bg-muted p-4 text-sm">
              <p className="font-medium">Response:</p>
              <p className="text-muted-foreground">{mutation.data.message}</p>
            </div>
          )}

          {mutation.isError && (
            <div className="mt-4 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
              {mutation.error.message}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
