<script lang="ts">
    export let level: number
</script>

{#if level == 1}
    <h1><slot></slot></h1>
{:else if level == 2}
    <h2><slot></slot></h2>
{:else if level == 3}
    <h3><slot></slot></h3>
{:else if level == 4}
    <h4><slot></slot></h4>
{:else if level == 5}
    <h5><slot></slot></h5>
{:else if level == 6}
    <h6><slot></slot></h6>
{:else}
    <p><b><slot></slot></b></p>
{/if}