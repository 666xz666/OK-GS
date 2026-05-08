function submitTask(event, endpoint) {
  event.preventDefault();
  var form = event.target;
  var data = new FormData(form);
  var logPanel = document.getElementById('log-panel');
  if (logPanel) {
    logPanel.textContent = 'Submitting task...';
  }

  fetch(endpoint, { method: 'POST', body: data })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
      if (resp.error) {
        if (logPanel) logPanel.textContent = 'ERROR: ' + resp.error;
        alert('Error: ' + resp.error);
        return;
      }
      if (logPanel) logPanel.textContent = 'Task ' + resp.task_id + ' started.\n';
      if (resp.redirect) {
        var taskId = resp.task_id;
        connectSSE(taskId, logPanel);
      }
    })
    .catch(function(err) {
      if (logPanel) logPanel.textContent = 'ERROR: ' + err;
    });
}

function connectSSE(taskId, logPanel) {
  if (!logPanel) return;
  var es = new EventSource('/tasks/' + taskId + '/log');
  es.onmessage = function(e) {
    var msg = e.data;
    if (msg.startsWith('__STATUS__:')) {
      var status = msg.replace('__STATUS__:', '');
      logPanel.textContent += '\n--- Task ' + status + ' ---\n';
      es.close();
    } else if (msg.startsWith('__ERROR__:')) {
      logPanel.textContent += '\nERROR: ' + msg.replace('__ERROR__:', '') + '\n';
    } else {
      logPanel.textContent += msg;
    }
    logPanel.scrollTop = logPanel.scrollHeight;
  };
  es.onerror = function() {
    es.close();
  };
}

function viewLog(taskId) {
  var card = document.getElementById('log-card');
  var panel = document.getElementById('log-panel');
  var label = document.getElementById('log-task-id');
  if (card) card.style.display = 'block';
  if (label) label.textContent = taskId;
  if (panel) {
    panel.textContent = 'Connecting...\n';
    connectSSE(taskId, panel);
  }
}

function pollTaskStatus() {
  var rows = document.querySelectorAll('tr[id^="task-"]');
  rows.forEach(function(row) {
    var taskId = row.id.replace('task-', '');
    fetch('/tasks/' + taskId + '/status')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var badge = row.querySelector('.badge');
        if (badge && data.status) {
          badge.className = 'badge bg-' + ({
            'pending': 'secondary', 'running': 'primary',
            'completed': 'success', 'failed': 'danger'
          })[data.status] || 'secondary';
          badge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        }
      });
  });
}

setInterval(pollTaskStatus, 5000);
