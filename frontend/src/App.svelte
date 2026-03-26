<script lang="ts">
  import { onRouteChange, parseRoute, currentPath, type Route } from "./lib/router";
  import Dashboard from "./routes/Dashboard.svelte";

  let path = $state(currentPath());
  let route: Route = $derived(parseRoute(path));

  onRouteChange(() => {
    path = currentPath();
  });
</script>

<div class="h-screen overflow-hidden bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100">
  <Dashboard {route} />
</div>
