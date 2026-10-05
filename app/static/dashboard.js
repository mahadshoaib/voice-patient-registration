"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  let key = "",
    patients = [],
    appointments = [],
    schedule = null,
    selected = null;
  let generation = 0,
    busy = false;
  const formatTime = (value) =>
    new Intl.DateTimeFormat("en-US", {
      dateStyle: "full",
      timeStyle: "short",
      timeZone: "UTC",
    }).format(new Date(value)) + " UTC";
  const text = (tag, value, className) => {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    return node;
  };
  function message(value = "", error = false) {
    $("message").textContent = value;
    $("message").className = error ? "error" : "success";
  }
  function lock() {
    generation++;
    key = "";
    patients = [];
    appointments = [];
    schedule = null;
    selected = null;
    $("api-key").value = "";
    $("search").value = "";
    $("patient-list").replaceChildren();
    $("demographics").replaceChildren();
    $("appointments").replaceChildren();
    $("patient-name").textContent = $("patient-id").textContent = "";
    $("workspace").hidden = true;
    $("login-panel").hidden = false;
    message();
    $("api-key").focus();
  }
  async function api(path, options = {}) {
    const requestKey = key;
    const response = await fetch(path, {
      ...options,
      cache: "no-store",
      headers: { "X-API-Key": requestKey, "Content-Type": "application/json" },
    });
    if (response.status === 401 || response.status === 403) {
      if (key === requestKey) lock();
      throw new Error("Access denied. Check your reviewer API key.");
    }
    const body = await response.json();
    if (!response.ok)
      throw new Error(
        body.error?.message || "Request failed. Please try again.",
      );
    return body.data;
  }
  function renderPatients() {
    const query = $("search").value.trim().toLowerCase();
    const visible = patients.filter((p) =>
      `${p.first_name} ${p.last_name} ${p.phone_number} ${p.email || ""}`
        .toLowerCase()
        .includes(query),
    );
    $("patient-list").replaceChildren();
    if (!visible.length)
      $("patient-list").append(
        text(
          "p",
          patients.length
            ? "No patients match your search."
            : "No registrations yet. Register through the voice agent or API.",
          "muted",
        ),
      );
    visible.forEach((p) => {
      const row = text(
        "button",
        "",
        "patient-row" + (selected === p.patient_id ? " active" : ""),
      );
      row.type = "button";
      row.setAttribute("aria-pressed", String(selected === p.patient_id));
      row.append(
        text(
          "span",
          (p.first_name[0] + p.last_name[0]).toUpperCase(),
          "avatar",
        ),
      );
      const label = text("span", "");
      label.append(
        text("strong", `${p.first_name} ${p.last_name}`),
        text("small", p.phone_number),
      );
      row.append(label);
      row.addEventListener("click", () => {
        selected = p.patient_id;
        renderPatients();
        renderDetails();
      });
      $("patient-list").append(row);
    });
  }
  function renderDetails() {
    const p = patients.find((p) => p.patient_id === selected);
    $("empty-selection").hidden = !!p;
    $("patient-details").hidden = !p;
    if (!p) return;
    $("patient-name").textContent = `${p.first_name} ${p.last_name}`;
    $("patient-id").textContent = `Record ${p.patient_id}`;
    $("demographics").replaceChildren();
    const fields = {
      "Date of birth": p.date_of_birth,
      Sex: p.sex,
      Phone: p.phone_number,
      Email: p.email,
      "Street address": [p.address_line_1, p.address_line_2]
        .filter(Boolean)
        .join(", "),
      "City / state / ZIP": `${p.city}, ${p.state} ${p.zip_code}`,
      Language: p.preferred_language,
      "Insurance provider": p.insurance_provider,
      "Member ID": p.insurance_member_id,
      "Emergency contact": p.emergency_contact_name,
      "Emergency phone": p.emergency_contact_phone,
      Registered: formatTime(p.created_at),
      "Last updated": formatTime(p.updated_at),
    };
    for (const [label, value] of Object.entries(fields)) {
      const group = text("div", "");
      group.append(text("dt", label), text("dd", value || "Not provided"));
      $("demographics").append(group);
    }
    $("schedule-description").textContent = schedule.description;
    const oldSlot = $("slot").value;
    $("slot").replaceChildren(new Option("Choose a time", ""));
    schedule.slots.forEach((value) =>
      $("slot").append(new Option(formatTime(value), value)),
    );
    if (schedule.slots.includes(oldSlot)) $("slot").value = oldSlot;
    $("slot-empty").hidden = schedule.slots.length > 0;
    $("booking-form").hidden = !schedule.slots.length;
    $("appointments").replaceChildren();
    const visits = appointments.filter((a) => a.patient_id === p.patient_id);
    if (!visits.length)
      $("appointments").append(
        text("p", "No appointments for this patient.", "muted"),
      );
    visits.forEach((a) => {
      const row = text("div", "", "visit");
      const label = text("div", "");
      label.append(
        text("strong", formatTime(a.starts_at)),
        text(
          "small",
          a.cancelled_at
            ? "Cancelled"
            : new Date(a.starts_at) <= new Date()
              ? "Past appointment"
              : "Booked · 30 minutes",
        ),
      );
      row.append(label);
      if (!a.cancelled_at && new Date(a.starts_at) > new Date()) {
        const cancel = text("button", "Cancel", "secondary");
        cancel.type = "button";
        cancel.disabled = busy;
        cancel.addEventListener("click", () => {
          if (
            confirm(
              `Cancel the demonstration appointment for ${p.first_name} ${p.last_name} on ${formatTime(a.starts_at)}?`,
            )
          ) {
            mutate(
              `/appointments/${a.appointment_id}`,
              { method: "DELETE" },
              "Appointment cancelled. The slot is available again.",
            );
          }
        });
        row.append(cancel);
      }
      $("appointments").append(row);
    });
  }
  async function refresh() {
    const ticket = ++generation;
    const result = await Promise.all([
      api("/patients"),
      api("/appointments"),
      api("/appointments/slots"),
    ]);
    if (ticket !== generation || !key) return;
    [patients, appointments, schedule] = result;
    if (!patients.some((p) => p.patient_id === selected)) selected = null;
    $("patient-count").textContent = patients.length;
    $("appointment-count").textContent = appointments.filter(
      (a) => !a.cancelled_at && new Date(a.starts_at) > new Date(),
    ).length;
    $("updated").textContent =
      "Updated " +
      new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    $("login-panel").hidden = true;
    $("workspace").hidden = false;
    renderPatients();
    renderDetails();
  }
  async function mutate(path, options, success) {
    if (busy) return;
    busy = true;
    $("book").disabled = true;
    renderDetails();
    try {
      await api(path, options);
      message(success);
      try {
        await refresh();
      } catch (error) {
        message(`${success} Refresh failed: ${error.message}`, true);
      }
    } catch (error) {
      message(error.message, true);
      if (key) {
        try {
          await refresh();
        } catch {
          /* Preserve the original error. */
        }
      }
    } finally {
      busy = false;
      $("book").disabled = false;
      if (key && schedule) renderDetails();
    }
  }
  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    key = $("api-key").value.trim();
    $("api-key").value = "";
    $("connect").disabled = true;
    message("Connecting…");
    try {
      await refresh();
      message();
    } catch (error) {
      message(error.message, true);
    } finally {
      $("connect").disabled = false;
    }
  });
  $("refresh").addEventListener("click", async () => {
    $("refresh").disabled = true;
    try {
      await refresh();
      message("Records refreshed.");
    } catch (error) {
      message(error.message, true);
    } finally {
      $("refresh").disabled = false;
    }
  });
  $("logout").addEventListener("click", lock);
  $("search").addEventListener("input", renderPatients);
  $("booking-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const patient = patients.find((p) => p.patient_id === selected),
      slot = $("slot").value;
    if (!patient || !slot || busy) return;
    if (
      confirm(
        `Book a 30-minute demonstration appointment for ${patient.first_name} ${patient.last_name} on ${formatTime(slot)}? This is not a real clinic visit.`,
      )
    ) {
      mutate(
        "/appointments",
        {
          method: "POST",
          body: JSON.stringify({ patient_id: selected, starts_at: slot }),
        },
        "Demonstration appointment booked.",
      );
    }
  });
})();
