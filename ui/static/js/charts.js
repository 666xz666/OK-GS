// Chart.js helper functions for model metrics visualization

function renderMetricsBarChart(canvasId, original, vq) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['SSIM', 'PSNR', 'LPIPS'],
      datasets: [
        { label: 'Original', data: [original.SSIM, original.PSNR, original.LPIPS], backgroundColor: '#0d6efd' },
        { label: 'VQ', data: [vq.SSIM, vq.PSNR, vq.LPIPS], backgroundColor: '#dc3545' }
      ]
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: false } },
      plugins: { legend: { position: 'bottom' } }
    }
  });
}

function renderStorageChart(canvasId, originalMb, vqMb) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Storage (MB)'],
      datasets: [
        { label: 'Original PLY', data: [originalMb], backgroundColor: '#0d6efd' },
        { label: 'VQ Zip', data: [vqMb], backgroundColor: '#198754' }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      scales: { x: { beginAtZero: true } },
      plugins: { legend: { position: 'bottom' } }
    }
  });
}
