var I = window.I18N || {};

function submitTask(event, endpoint) {
  event.preventDefault();
  var form = event.target;
  var data = new FormData(form);
  var logPanel = document.getElementById('log-panel');
  if (logPanel) {
    logPanel.textContent = I.submitting_task || 'Submitting task...';
  }

  fetch(endpoint, { method: 'POST', body: data })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
      var errPrefix = I.error_prefix || 'ERROR: ';
      if (resp.error) {
        if (logPanel) logPanel.textContent = errPrefix + resp.error;
        alert(errPrefix + resp.error);
        return;
      }
      var started = I.task_started || 'Task {id} started.\n';
      if (logPanel) logPanel.textContent = started.replace('{id}', resp.task_id);
      if (resp.redirect) {
        var taskId = resp.task_id;
        connectSSE(taskId, logPanel);
      }
    })
    .catch(function(err) {
      if (logPanel) logPanel.textContent = (I.error_prefix || 'ERROR: ') + err;
    });
}

function connectSSE(taskId, logPanel) {
  if (!logPanel) return;
  var es = new EventSource('/tasks/' + taskId + '/log');
  es.onmessage = function(e) {
    var msg = e.data;
    if (msg.startsWith('__STATUS__:')) {
      var status = msg.replace('__STATUS__:', '');
      var statusMsg = I.task_status || '\n--- Task {status} ---\n';
      logPanel.textContent += statusMsg.replace('{status}', status);
      es.close();
    } else if (msg.startsWith('__ERROR__:')) {
      logPanel.textContent += '\n' + (I.error_prefix || 'ERROR: ') + msg.replace('__ERROR__:', '') + '\n';
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
    panel.textContent = (I.connecting || 'Connecting...') + '\n';
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
          var badgeLabels = {
            'pending': I.badge_pending || 'Pending',
            'running': I.badge_running || 'Running',
            'completed': I.badge_completed || 'Completed',
            'failed': I.badge_failed || 'Failed'
          };
          var badgeClasses = {
            'pending': 'secondary', 'running': 'primary',
            'completed': 'success', 'failed': 'danger'
          };
          badge.className = 'badge bg-' + (badgeClasses[data.status] || 'secondary');
          badge.textContent = badgeLabels[data.status] || data.status;
        }
      });
  });
}

setInterval(pollTaskStatus, 5000);
