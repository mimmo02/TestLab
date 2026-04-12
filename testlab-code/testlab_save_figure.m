function testlab_save_figure(fig_handle)
% TESTLAB_SAVE_FIGURE  Salva la figura nel path definito da TESTLAB_EXPORT_PATH.
% Se la variabile non è impostata, non fa nulla (la figura resta aperta).
%
% Uso nello script .m:
%   testlab_save_figure(gcf)

export_path = getenv('TESTLAB_EXPORT_PATH');
if isempty(export_path)
    return
end

[parent_dir, ~, ~] = fileparts(export_path);
if ~isempty(parent_dir) && ~exist(parent_dir, 'dir')
    mkdir(parent_dir);
end

[~, ~, ext] = fileparts(export_path);
fmt = lower(strrep(ext, '.', ''));
if isempty(fmt)
    fmt = 'png';
end

switch fmt
    case 'pdf'
        exportgraphics(fig_handle, export_path, 'ContentType', 'vector');
    case 'svg'
        exportgraphics(fig_handle, export_path, 'ContentType', 'vector');
    otherwise
        exportgraphics(fig_handle, export_path);
end

fprintf('[testlab] figura salvata in: %s\n', export_path);
end
