var I = window.I18N || {};
var APP_STATE = window.APP_STATE || { hasActiveTask: false };

function getTaskFormBlockReason(form) {
  if (!form) return '';
  if (APP_STATE.hasActiveTask) {
    return I.active_task_blocked || 'Another task is already running.';
  }

  var selectName = form.getAttribute('data-model-select');
  var completionAttr = form.getAttribute('data-completion-attr');
  if (!selectName || !completionAttr) {
    return '';
  }

  var select = form.querySelector('[name="' + selectName + '"]');
  if (!select || select.selectedIndex < 0) {
    return '';
  }

  var option = select.options[select.selectedIndex];
  if (option && option.value && option.getAttribute(completionAttr) === 'true') {
    return form.getAttribute('data-completed-message') || (I.error_prefix || 'ERROR');
  }

  return '';
}

function updateTaskFormState(form) {
  if (!form) return;
  var submitButton = form.querySelector('.task-submit-btn') || form.querySelector('button[type="submit"]');
  var note = form.querySelector('.task-submit-note');
  var blockReason = getTaskFormBlockReason(form);

  if (submitButton) {
    submitButton.disabled = !!blockReason;
  }
  if (note) {
    note.textContent = blockReason;
  }
}

function updateAllTaskFormStates() {
  document.querySelectorAll('form[data-task-form="true"]').forEach(function(form) {
    updateTaskFormState(form);
  });
}

function initTaskForms() {
  document.querySelectorAll('form[data-task-form="true"]').forEach(function(form) {
    if (form.dataset.taskFormBound === 'true') {
      updateTaskFormState(form);
      return;
    }

    var selectName = form.getAttribute('data-model-select');
    if (selectName) {
      var select = form.querySelector('[name="' + selectName + '"]');
      if (select) {
        select.addEventListener('change', function() {
          updateTaskFormState(form);
        });
      }
    }

    form.dataset.taskFormBound = 'true';
    updateTaskFormState(form);
  });
}

function submitTask(event, endpoint) {
  event.preventDefault();
  var form = event.target;
  var blockReason = getTaskFormBlockReason(form);
  var data = new FormData(form);
  var logPanel = document.getElementById('log-panel');
  if (blockReason) {
    if (logPanel) {
      logPanel.textContent = blockReason;
    }
    updateTaskFormState(form);
    return;
  }
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
      APP_STATE.hasActiveTask = true;
      updateAllTaskFormStates();
      if (resp.redirect) {
        var taskId = resp.task_id;
        connectSSE(taskId, logPanel);
      }
    })
    .catch(function(err) {
      if (logPanel) logPanel.textContent = (I.error_prefix || 'ERROR: ') + err;
    });
}

function pollActiveTaskState() {
  fetch('/tasks/summary')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      APP_STATE.hasActiveTask = !!data.has_active_task;
      updateAllTaskFormStates();
    })
    .catch(function() {});
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
      APP_STATE.hasActiveTask = false;
      updateAllTaskFormStates();
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

setInterval(function() {
  pollTaskStatus();
  pollActiveTaskState();
}, 5000);
