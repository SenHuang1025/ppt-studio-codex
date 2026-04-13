<template>
  <div class="pointer-events-none absolute inset-0 overflow-hidden">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.42),transparent_42%)]" />
    <div class="paper-wash blob-sage absolute -left-24 top-[-6%] h-[28rem] w-[28rem] rounded-full" />
    <div class="paper-wash blob-amber absolute right-[-8%] top-[16%] h-[24rem] w-[24rem] rounded-full" />
    <div class="paper-wash blob-earth absolute bottom-[-8%] left-[24%] h-[22rem] w-[22rem] rounded-full" />
    <div class="grain-overlay absolute inset-0 opacity-40" />
    <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(245,236,215,0.12)_0%,rgba(245,236,215,0.58)_56%,rgba(235,226,205,0.92)_100%)]" />
  </div>
</template>

<style scoped>
.paper-wash {
  filter: blur(72px);
  animation: drift 24s ease-in-out infinite;
  will-change: transform, opacity;
}

.blob-sage {
  background: radial-gradient(circle, var(--ambient-sage) 0%, transparent 70%);
}

.blob-amber {
  background: radial-gradient(circle, var(--ambient-amber) 0%, transparent 70%);
  animation-delay: -7s;
}

.blob-earth {
  background: radial-gradient(circle, var(--ambient-earth) 0%, transparent 72%);
  animation-delay: -12s;
}

.grain-overlay {
  background-image:
    linear-gradient(to right, var(--app-grid-line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--app-grid-line) 1px, transparent 1px);
  background-position: center;
  background-size: 120px 120px;
  mask-image: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.45) 15%, rgba(0, 0, 0, 1) 100%);
}

@keyframes drift {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0.42;
  }

  50% {
    transform: translate3d(18px, -14px, 0) scale(1.05);
    opacity: 0.6;
  }
}
</style>
