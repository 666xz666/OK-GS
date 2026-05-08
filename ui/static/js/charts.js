// OK-GS Web UI — Chart helpers

function renderMetricsBarChart(canvasId, original, vq, labels) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  labels = labels || { ssim: 'SSIM', psnr: 'PSNR', lpips: 'LPIPS', original: 'Original', vq: 'VQ' };
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [labels.ssim, labels.psnr, labels.lpips],
      datasets: [
        { label: labels.original, data: [original.SSIM, original.PSNR, original.LPIPS],
          backgroundColor: '#6366f1', borderRadius: 6 },
        { label: labels.vq, data: [vq.SSIM, vq.PSNR, vq.LPIPS],
          backgroundColor: '#f472b6', borderRadius: 6 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: false, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
      }
    }
  });
}

function renderStorageChart(canvasId, originalMb, vqMb, labels) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  labels = labels || { storage: 'Storage (MB)', original: 'Original PLY', vq: 'VQ Zip' };
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [labels.storage],
      datasets: [
        { label: labels.original, data: [originalMb],
          backgroundColor: '#6366f1', borderRadius: 6 },
        { label: labels.vq, data: [vqMb],
          backgroundColor: '#10b981', borderRadius: 6 }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        y: { grid: { display: false } }
      },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
      }
    }
  });
}

function renderPerViewChart(canvasId, perViewData, labels) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  labels = labels || { ssim: 'SSIM', psnr: 'PSNR', lpips: 'LPIPS' };

  var views = [];
  var ssim = [];
  var psnr = [];
  var lpips = [];

  perViewData.forEach(function(row, i) {
    views.push(row.image || ('#' + (i + 1)));
    ssim.push(row.SSIM);
    psnr.push(row.PSNR);
    lpips.push(row.LPIPS);
  });

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: views,
      datasets: [
        {
          label: labels.ssim,
          data: ssim,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 1.5,
          pointHoverRadius: 5,
          borderWidth: 2
        },
        {
          label: labels.psnr,
          data: psnr,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,0.06)',
          fill: true,
          tension: 0.35,
          pointRadius: 1.5,
          pointHoverRadius: 5,
          borderWidth: 2
        },
        {
          label: labels.lpips,
          data: lpips,
          borderColor: '#f472b6',
          backgroundColor: 'rgba(244,114,182,0.05)',
          fill: true,
          tension: 0.35,
          pointRadius: 1.5,
          pointHoverRadius: 5,
          borderWidth: 2,
          borderDash: [5, 3]
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 10, maxRotation: 0 }
        },
        y: {
          beginAtZero: false,
          grid: { color: '#f1f5f9' }
        }
      },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
      }
    }
  });
}
