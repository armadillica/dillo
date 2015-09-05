var gulp          = require('gulp'),
    sass          = require('gulp-sass'),
    sourcemaps    = require('gulp-sourcemaps'),
    autoprefixer  = require('gulp-autoprefixer'),
    jade          = require('gulp-jade'),
    uglify        = require('gulp-uglify'),
    livereload    = require('gulp-livereload');

/* CSS */
gulp.task('styles', function() {
    gulp.src('dillo/src/styles/**/*.sass')
        .pipe(sourcemaps.init())
        .pipe(sass({
            outputStyle: 'compressed'}
            ))
        .pipe(autoprefixer("last 3 version", "safari 5", "ie 8", "ie 9"))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest('dillo/application/static/assets/css'))
        .pipe(livereload());
});

/* Templates - Jade */
gulp.task('templates', function() {
    gulp.src('dillo/src/templates/**/*.jade')
        .pipe(jade({
            pretty: true
        }))
        .pipe(gulp.dest('dillo/application/templates/'))
        .pipe(livereload());
});

/* Scripts */
gulp.task('scripts', function() {
    gulp.src('dillo/src/scripts/uglify/**/*.js')
        .pipe(gulp.dest('dillo/application/static/js/'))
        .pipe(livereload());
});

// While developing, run 'gulp watch'
gulp.task('watch',function() {
    livereload.listen();

    gulp.watch('dillo/src/styles/**/*.sass',['styles']);
    gulp.watch('dillo/src/templates/**/*.jade',['templates']);
    gulp.watch('dillo/src/scripts/uglify/**/*.js',['templates']);
});

// Run 'gulp' to build everything at once
gulp.task('default', ['styles', 'templates']);
