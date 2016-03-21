var gulp          = require('gulp'),
    plumber       = require('gulp-plumber'),
    sass          = require('gulp-sass'),
    sourcemaps    = require('gulp-sourcemaps'),
    autoprefixer  = require('gulp-autoprefixer'),
    jade          = require('gulp-jade'),
    uglify        = require('gulp-uglify'),
    concat        = require('gulp-concat'),
    livereload    = require('gulp-livereload');

/* CSS */
gulp.task('styles', function() {
    gulp.src('dillo/src/themes/dillo/styles/**/*.sass')
        .pipe(plumber())
        .pipe(sourcemaps.init())
        .pipe(sass({
            outputStyle: 'compressed'}
            ))
        .pipe(autoprefixer("last 3 versions", "safari 5", "ie 8", "ie 9"))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest('dillo/application/themes/dillo/static/css'))
        .pipe(livereload());
});

/* Templates - Jade */
gulp.task('templates', function() {
    gulp.src('dillo/src/templates/**/*.jade')
        .pipe(jade({
            pretty: true
        }))
        .pipe(gulp.dest('dillo/application/templates'))
        .pipe(livereload());
    /* Templates for Dillo theme */
    gulp.src('dillo/src/themes/dillo/templates/**/*.jade')
        .pipe(jade({
            pretty: true
        }))
        .pipe(gulp.dest('dillo/application/themes/dillo/templates'))
        .pipe(livereload());
});

/* Scripts */
gulp.task('scripts', function() {
    gulp.src('dillo/src/themes/dillo/scripts/uglify/**/*.js')
        .pipe(sourcemaps.init())
        .pipe(concat("tutti.min.js"))
        .pipe(uglify())
        .pipe(sourcemaps.write("./"))
        .pipe(gulp.dest('dillo/application/themes/dillo/static/js'))
        .pipe(livereload());
});

// While developing, run 'gulp watch'
gulp.task('watch',function() {
    livereload.listen();

    gulp.watch('dillo/src/themes/dillo/styles/**/*.sass',['styles']);
    gulp.watch('dillo/src/templates/**/*.jade',['templates']);
    gulp.watch('dillo/src/themes/dillo/templates/**/*.jade',['templates']);
    gulp.watch('dillo/src/themes/dillo/scripts/uglify/**/*.js',['scripts']);
});

// Run 'gulp' to build everything at once
gulp.task('default', ['styles', 'templates', 'scripts']);
