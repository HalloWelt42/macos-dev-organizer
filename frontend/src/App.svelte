<script lang="ts">
  import { onRouteChange, projectIdFromPath, currentPath } from "./lib/router";
  import Dashboard from "./routes/Dashboard.svelte";

  let path = $state(currentPath());
  let projectId = $derived(projectIdFromPath(path));

  onRouteChange(() => {
    path = currentPath();
  });
</script>

<div class="h-screen overflow-hidden bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100">
  <Dashboard selectedProjectIdFromRoute={projectId} />
</div>
