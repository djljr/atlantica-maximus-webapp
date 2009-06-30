from django.conf.urls.defaults import patterns

urlpatterns = patterns('maximus.views',
    (r'^$', 'index'),
    (r'^teams$', 'create_team'),
    (r'^teams/edit$', 'edit_team'),
    (r'^results/detail$', 'result_detail'),
    (r'^tournament$', 'create_tournament'),
    (r'^tournament/matchups$', 'view_tournament'),
    (r'^tournament/matchups/result$', 'result_tournament'),
)
