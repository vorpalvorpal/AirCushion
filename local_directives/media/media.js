//fullscreen

var fullscreenElements = document.getElementsByClassName("media-fullscreen");
Array.prototype.forEach.call(fullscreenElements, function(element) {
  var container = element.closest(".step");
  // center element within container
  container.style.display = 'flex'; container.style.justifyContent = 'center'; container.style.alignItems = 'center';
  scaleContainer(container); // set initial scaling
  window.addEventListener("resize", function() { // re-scale after each resize
    setTimeout(function() { scaleContainer(container); }, 10); // timeout prevents excessive processing load during resizing
  }, false);
});

var scaleMax = 100
function scaleContainer(container) { // 768 & 1024 from config.height & width in impress.js
  scaleMax = Math.round(Math.max(100/(window.innerHeight/768), 100/(window.innerWidth/1024))*100)/100 
  container.style.height = scaleMax + 'vh';
  container.style.width = scaleMax + 'vw';
}

// autoplay
// based on work by matejmosko https://github.com/impress/impress.js/issues/100

// Video
var videos = document.getElementsByTagName("video");
Array.prototype.forEach.call(videos, function(video) {
  if (video.hasAttribute("data-media-autoplay")) {
    var videoStep = video.closest(".step");
    videoStep.addEventListener("impress:stepenter", function() {setTimeout(function() {video.play();}, 500);}, false);
    videoStep.addEventListener("impress:stepleave", function() {video.pause();}, false);
  };
});


// Audio
var audios = document.getElementsByTagName("audio");
Array.prototype.forEach.call(audios, function(audio) {
  if (audio.hasAttribute("data-media-autoplay")) {
    var audioStep = audio.closest(".step");
    audioStep.addEventListener("impress:stepenter", function() {setTimeout(function() {audio.play();}, 500);}, false);
    audioStep.addEventListener("impress:stepleave", function() {audio.pause();}, false);
  };
});
