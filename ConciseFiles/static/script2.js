// script.js
function downloadVideo() {
    const url = $("#url").val();
    $.ajax({
        url: "/download",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ url: url }),
        success: function(response) {
            if ("progress" in response) {
                const progress = parseFloat(response.progress.replace("%", ""));
                $("#progress-bar").css("width", progress + "%");
                if (progress < 100) {
                    $("#progress-container").show();
                } else {
                    $("#progress-container").hide();
                }
            } else {
                $("#progress-container").hide();
                alert(response.message);
            }
        },
        error: function(xhr, status, error) {
            $("#progress-container").hide();
            if (xhr.status === 400) {
                alert(xhr.responseJSON.message);
            } else {
                alert("Server error occurred");
            }
        }
    });
}
