<script lang="ts">
    export let tree: any
</script>

<ul>
    {#each tree as item}
        <li>
            <span>[{item.type}]</span>
            {#if item.children}
                <svelte:self tree={item.children} />
            {/if}
        </li>
    {/each}
</ul>